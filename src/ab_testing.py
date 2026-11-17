"""A/B testing between two served models (ticket #52): traffic split and winner decision.

Pure Python (no FastAPI, no database). `app/api.py` assigns the variant of each
request with `choose_variant`, `database.ab_metrics` counts the labelled
feedback per variant and `build_report` turns those counts into the decision.
"""
import math
import os
import random

VARIANTS = ("A", "B")  # A = control (current model), B = challenger
MODEL_VERSIONS = {
    "A": os.getenv("MODEL_VERSION_A", "0.1.0"),
    "B": os.getenv("MODEL_VERSION_B", "0.2.0"),
}

# Decision rule: enough labelled feedback, a significant difference and a
# difference big enough to matter. Documented in docs/AB_TESTING.md.
MIN_FEEDBACK_PER_VARIANT = 200
ALPHA = 0.05
MIN_EFFECT = 0.005  # 0.5 accuracy points


def traffic_share_b(value=None) -> float:
    """Share of the traffic sent to B, from `value` or the AB_TRAFFIC_B variable (default 0)."""
    raw = os.getenv("AB_TRAFFIC_B", "0") if value is None else value
    try:
        share = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"AB_TRAFFIC_B must be a number between 0 and 1, got {raw!r}.") from None
    if not 0.0 <= share <= 1.0:
        raise ValueError(f"AB_TRAFFIC_B must be between 0 and 1, got {share}.")
    return share


def choose_variant(share_b: float, b_ready: bool, forced: str | None = None, rng=random) -> str:
    """Variant that serves a request.

    `forced` ("A" or "B", any case) wins over the split. Without it, a request
    goes to B with probability `share_b`, and always to A while B is not
    loaded or the split is 0 (A/B test disabled).
    """
    if forced is not None:
        variant = forced.upper()
        if variant not in VARIANTS:
            raise ValueError(f"Unknown variant {forced!r}. Expected one of {VARIANTS}.")
        return variant
    if not b_ready or share_b <= 0:
        return "A"
    return "B" if rng.random() < share_b else "A"


def two_proportion_ztest(correct_a: int, n_a: int, correct_b: int, n_b: int) -> dict:
    """Two-sided z-test of the difference between two accuracies (pooled variance).

    Returns `z` (positive when B is better) and the two-sided `p_value`.
    """
    p_a, p_b = correct_a / n_a, correct_b / n_b
    pooled = (correct_a + correct_b) / (n_a + n_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    if se == 0:  # both variants are always right (or always wrong): no difference
        return {"z": 0.0, "p_value": 1.0}
    z = (p_b - p_a) / se
    return {"z": z, "p_value": math.erfc(abs(z) / math.sqrt(2))}


def decide(stats_a: dict, stats_b: dict) -> dict:
    """Winner decision from the labelled feedback of each variant.

    `stats_*` need `feedback` (labelled predictions) and `correct`. The decision
    is `insufficient_data`, `inconclusive`, `winner_A` or `winner_B`.
    """
    n_a, n_b = int(stats_a["feedback"]), int(stats_b["feedback"])
    result = {"decision": "insufficient_data", "difference": None, "z": None, "p_value": None}
    if min(n_a, n_b) < MIN_FEEDBACK_PER_VARIANT:
        return result
    test = two_proportion_ztest(int(stats_a["correct"]), n_a, int(stats_b["correct"]), n_b)
    difference = int(stats_b["correct"]) / n_b - int(stats_a["correct"]) / n_a  # B minus A
    significant = test["p_value"] < ALPHA and abs(difference) >= MIN_EFFECT
    if significant:
        result["decision"] = "winner_B" if difference > 0 else "winner_A"
    else:
        result["decision"] = "inconclusive"
    result.update(difference=difference, z=test["z"], p_value=test["p_value"])
    return result


def mcnemar_test(only_a_correct: int, only_b_correct: int) -> dict:
    """McNemar test (continuity-corrected) for two models scored on the same rows.

    `only_a_correct` counts the rows A got right and B wrong, `only_b_correct`
    the reverse. Rows both models get right or wrong do not matter. Returns the
    chi-square `statistic` (1 degree of freedom) and its `p_value`.
    """
    discordant = only_a_correct + only_b_correct
    if discordant == 0:
        return {"statistic": 0.0, "p_value": 1.0}
    statistic = max(abs(only_a_correct - only_b_correct) - 1, 0) ** 2 / discordant
    return {"statistic": statistic, "p_value": math.erfc(math.sqrt(statistic / 2))}


def build_report(stats: dict) -> dict:
    """Per-variant metrics plus the decision; `stats` is `database.ab_metrics()`."""
    variants = {}
    for name in VARIANTS:
        item = dict(stats[name])
        feedback = item["feedback"]
        item["live_accuracy"] = item["correct"] / feedback if feedback else None
        variants[name] = item
    report = {"variants": variants, **decide(stats["A"], stats["B"])}
    report["rule"] = {
        "min_feedback_per_variant": MIN_FEEDBACK_PER_VARIANT,
        "alpha": ALPHA,
        "min_effect": MIN_EFFECT,
    }
    return report