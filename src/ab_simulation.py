"""Offline A/B simulation (ticket #52): replay the validation set through the two served models.

It reuses the production pieces: `choose_variant` splits the traffic, the
predictions and feedback are stored with `database.save_prediction` /
`save_feedback` (on a temporary SQLite file) and the result comes from
`ab_metrics` + `build_report`, exactly like `GET /ab/results`. The true label of
each row stands in for the user feedback, which assumes every prediction is
labelled; in production feedback is partial, so the real test needs more traffic.

Three parts:
  1. Offline comparison of both models on the whole validation set (McNemar test).
  2. A/B simulation: A = main model, B = challenger.
  3. A/A control: B serves the same model as A, so no winner should be declared.

Run it with the pinned versions, inside Docker, after exporting both models:

    docker compose run --rm --no-deps app python src/ab_simulation.py [n_requests] [share_b] [seed]
"""
import random
import sys
import tempfile
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # the `app` package is not on the path of src/ scripts

from ab_testing import (  # noqa: E402
    MODEL_VERSIONS,
    build_report,
    choose_variant,
    mcnemar_test,
    traffic_share_b,
)
from app.serving import MODEL_B_PATH, MODEL_PATH, load_model  # noqa: E402
from data_audit import load_raw  # noqa: E402
from data_cleaning import (  # noqa: E402
    FEATURES,
    NUMERIC_FEATURES,
    SOIL_FEATURES,
    TARGET,
    WILDERNESS_FEATURES,
    clean,
)
from data_split import RANDOM_STATE, split_train_val_test  # noqa: E402
from database import ab_metrics, save_feedback, save_prediction  # noqa: E402
from target_encoding import CLASS_NAMES  # noqa: E402

N_REQUESTS = 10_000
SHARE_B = 0.5


def load_models():
    """Both served models, or exit with the reason one of them is missing."""
    loaded_a, loaded_b = load_model(MODEL_PATH), load_model(MODEL_B_PATH)
    for name, loaded in (("A", loaded_a), ("B", loaded_b)):
        if not loaded.ready:
            raise SystemExit(
                f"Model {name} is not available: {loaded.error}\n"
                "Export it first (src/export_model.py, src/export_challenger.py)."
            )
    if loaded_a.cover_types != loaded_b.cover_types:
        raise SystemExit("The two models order their classes differently.")
    return loaded_a, loaded_b


def offline_comparison(y_val, proba_a, proba_b, cover_types) -> dict:
    """Accuracy, macro F1 and McNemar test of both models on the same rows."""
    classes = np.asarray(cover_types)
    y = y_val.to_numpy()
    pred_a, pred_b = classes[proba_a.argmax(axis=1)], classes[proba_b.argmax(axis=1)]
    right_a, right_b = pred_a == y, pred_b == y
    only_a, only_b = int((right_a & ~right_b).sum()), int((~right_a & right_b).sum())
    return {
        "accuracy_a": float(accuracy_score(y, pred_a)),
        "accuracy_b": float(accuracy_score(y, pred_b)),
        "macro_f1_a": float(f1_score(y, pred_a, average="macro", zero_division=0)),
        "macro_f1_b": float(f1_score(y, pred_b, average="macro", zero_division=0)),
        "only_a": only_a,
        "only_b": only_b,
        "mcnemar": mcnemar_test(only_a, only_b),
    }


def simulate(X_val, y_val, proba_a, proba_b, cover_types, n_requests, share_b, seed) -> dict:
    """Serve `n_requests` validation rows through the traffic split and return the A/B report."""
    rng = random.Random(seed)
    indices = np.random.default_rng(seed).choice(len(y_val), size=n_requests, replace=False)
    subset = X_val.iloc[indices]
    wilderness = subset[WILDERNESS_FEATURES].to_numpy().argmax(axis=1) + 1
    soil = subset[SOIL_FEATURES].to_numpy().argmax(axis=1) + 1
    numeric = subset[NUMERIC_FEATURES].to_numpy(dtype=float)
    labels = y_val.to_numpy()[indices]

    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{(Path(tmp) / 'ab_simulation.db').as_posix()}"
        for k, row_index in enumerate(indices):
            variant = choose_variant(share_b, True, rng=rng)
            probabilities = (proba_b if variant == "B" else proba_a)[row_index]
            best = int(probabilities.argmax())
            cover_type = cover_types[best]
            request = dict(zip(NUMERIC_FEATURES, numeric[k]))
            request.update(Wilderness_Area=int(wilderness[k]), Soil_Type=int(soil[k]))
            prediction = {
                "cover_type": cover_type,
                "class_name": CLASS_NAMES[cover_type],
                "confidence": float(probabilities[best]),
                "probabilities": {
                    CLASS_NAMES[ct]: float(p) for ct, p in zip(cover_types, probabilities)
                },
            }
            prediction_id = save_prediction(
                request, prediction, model_version=MODEL_VERSIONS[variant], variant=variant, db_url=url
            )
            save_feedback(prediction_id, int(labels[k]), db_url=url)
            if (k + 1) % 2000 == 0:
                print(f"  ... {k + 1:,} / {n_requests:,} requests", flush=True)
        return build_report(ab_metrics(url))


def _fmt(value, spec=".4f") -> str:
    return "-" if value is None else format(value, spec)


def print_report(title: str, report: dict) -> None:
    print(f"\n== {title} ==")
    print(f"{'variant':<9}{'model':<8}{'served':>8}{'feedback':>10}{'correct':>9}{'accuracy':>10}{'avg conf':>10}")
    for name in ("A", "B"):
        v = report["variants"][name]
        print(
            f"{name:<9}{v['model_version'] or '-':<8}{v['predictions']:>8,}{v['feedback']:>10,}"
            f"{v['correct']:>9,}{_fmt(v['live_accuracy']):>10}{_fmt(v['average_confidence']):>10}"
        )
    difference = None if report["difference"] is None else report["difference"] * 100
    print(f"Difference B - A: {_fmt(difference, '+.2f')} accuracy points")
    print(f"z = {_fmt(report['z'], '.3f')}   p-value = {_fmt(report['p_value'], '.4f')}")
    rule = report["rule"]
    print(
        f"Rule: >= {rule['min_feedback_per_variant']} feedback per variant, p < {rule['alpha']}, "
        f"difference >= {rule['min_effect'] * 100:.1f} points"
    )
    print(f"Decision: {report['decision']}")


def main() -> None:
    n_requests = int(sys.argv[1]) if len(sys.argv) > 1 else N_REQUESTS
    share_b = traffic_share_b(sys.argv[2]) if len(sys.argv) > 2 else SHARE_B
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else RANDOM_STATE

    df = clean(load_raw())
    _, X_val, _, _, y_val, _ = split_train_val_test(df[FEATURES], df[TARGET])
    if n_requests > len(y_val):
        raise SystemExit(f"n_requests={n_requests:,} exceeds the {len(y_val):,} validation rows.")

    loaded_a, loaded_b = load_models()
    cover_types = loaded_a.cover_types
    proba_a = loaded_a.model.predict_proba(X_val)
    proba_b = loaded_b.model.predict_proba(X_val)

    print(f"== A/B simulation: {n_requests:,} requests, {share_b:.0%} to B, seed {seed} ==")
    print(f"A = {MODEL_VERSIONS['A']} ({type(loaded_a.model.named_steps['model']).__name__}), "
          f"B = {MODEL_VERSIONS['B']} ({type(loaded_b.model.named_steps['model'].estimator_).__name__})")

    off = offline_comparison(y_val, proba_a, proba_b, cover_types)
    print(f"\n== Offline comparison on the validation set ({len(y_val):,} rows) ==")
    print(f"A: accuracy {off['accuracy_a']:.4f}  macro F1 {off['macro_f1_a']:.4f}")
    print(f"B: accuracy {off['accuracy_b']:.4f}  macro F1 {off['macro_f1_b']:.4f}")
    print(f"Rows only A gets right: {off['only_a']:,}   only B gets right: {off['only_b']:,}")
    print(f"McNemar chi2 = {off['mcnemar']['statistic']:.2f}   p-value = {off['mcnemar']['p_value']:.4g}")

    print("\nSimulating A/B ...", flush=True)
    print_report("A/B simulation (A = main model, B = challenger)",
                 simulate(X_val, y_val, proba_a, proba_b, cover_types, n_requests, share_b, seed))

    print("\nSimulating A/A control ...", flush=True)
    print_report("A/A control (B serves the same model as A: no winner expected)",
                 simulate(X_val, y_val, proba_a, proba_a, cover_types, n_requests, share_b, seed))


if __name__ == "__main__":
    main()