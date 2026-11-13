"""Feature engineering and selection (ticket #18): candidate features, screening and selection."""
import time

import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import FunctionTransformer
from xgboost import XGBClassifier

from baseline import evaluate_model
from data_audit import load_raw
from data_cleaning import FEATURES, SOIL_FEATURES, TARGET, WILDERNESS_FEATURES, clean
from data_split import split_train_val_test

RANDOM_STATE = 42
MIN_GAIN = 0.002  # screening: minimum improvement of the mean macro F1
SUBSET_TOLERANCE = 0.001  # selection: maximum macro F1 loss on validation
TOP_K = (20, 30, 40)
CONFIRM_SEED = 7  # different CV seed for the confirmation run
# Outcome of the screening (see docs/PREPROCESSING.md). Update it if the experiment is rerun.
SELECTED_GROUPS = ["elevation_offsets", "distance_combinations"]

HYDRO_H = "Horizontal_Distance_To_Hydrology"
HYDRO_V = "Vertical_Distance_To_Hydrology"
ROADS = "Horizontal_Distance_To_Roadways"
FIRE = "Horizontal_Distance_To_Fire_Points"


def _aspect_circular(X: pd.DataFrame) -> pd.DataFrame:
    radians = np.deg2rad(X["Aspect"])
    return pd.DataFrame(
        {"Aspect_sin": np.sin(radians), "Aspect_cos": np.cos(radians)}, index=X.index
    )


def _hydrology_distance(X: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {"Hydrology_Euclidean": np.sqrt(X[HYDRO_H] ** 2 + X[HYDRO_V] ** 2)}, index=X.index
    )


def _hydrology_ratio(X: pd.DataFrame) -> pd.DataFrame:
    # + 1 because many rows have a horizontal distance of 0.
    return pd.DataFrame(
        {"Hydrology_Slope_Ratio": X[HYDRO_V] / (X[HYDRO_H] + 1)}, index=X.index
    )


def _elevation_offsets(X: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Elevation_minus_VDH": X["Elevation"] - X[HYDRO_V],
            "Elevation_minus_HDH": X["Elevation"] - X[HYDRO_H],
        },
        index=X.index,
    )


def _distance_combinations(X: pd.DataFrame) -> pd.DataFrame:
    pairs = [
        ("Hydrology", HYDRO_H, "Roadways", ROADS),
        ("Hydrology", HYDRO_H, "Fire", FIRE),
        ("Roadways", ROADS, "Fire", FIRE),
    ]
    new = {}
    for name_a, col_a, name_b, col_b in pairs:
        new[f"{name_a}_plus_{name_b}"] = X[col_a] + X[col_b]
        new[f"{name_a}_absdiff_{name_b}"] = (X[col_a] - X[col_b]).abs()
    return pd.DataFrame(new, index=X.index)


def _category_ids(X: pd.DataFrame) -> pd.DataFrame:
    """Index (1-based) of the active one-hot indicator; 0 if not exactly one is active."""
    new = {}
    for name, columns in (
        ("Wilderness_Area_id", WILDERNESS_FEATURES),
        ("Soil_Type_id", SOIL_FEATURES),
    ):
        values = X[columns].to_numpy()
        new[name] = np.where(values.sum(axis=1) == 1, values.argmax(axis=1) + 1, 0)
    return pd.DataFrame(new, index=X.index)


FEATURE_GROUPS = {
    "aspect_circular": _aspect_circular,
    "hydrology_distance": _hydrology_distance,
    "hydrology_ratio": _hydrology_ratio,
    "elevation_offsets": _elevation_offsets,
    "distance_combinations": _distance_combinations,
    "category_ids": _category_ids,
}


def add_features(X: pd.DataFrame, groups=None) -> pd.DataFrame:
    """Return a new dataframe with the raw features plus the candidate feature groups.

    Pure and stateless: every new column is computed row by row, so nothing is
    learned from data and it cannot leak. `groups=None` adds every group.
    """
    groups = list(FEATURE_GROUPS) if groups is None else list(groups)
    unknown = [g for g in groups if g not in FEATURE_GROUPS]
    if unknown:
        raise ValueError(f"Unknown feature groups {unknown}. Choose from {list(FEATURE_GROUPS)}.")
    return pd.concat([X] + [FEATURE_GROUPS[g](X) for g in groups], axis=1)


def build_feature_engineer(groups=None) -> FunctionTransformer:
    """Stateless transformer for a scikit-learn Pipeline (DataFrame in, DataFrame out)."""
    return FunctionTransformer(
        add_features, kw_args={"groups": None if groups is None else list(groups)}
    )


def build_xgboost(n_jobs: int = 1, **params) -> XGBClassifier:
    """XGBoost with default hyperparameters. Labels must be 0-based (use y - 1)."""
    return XGBClassifier(random_state=RANDOM_STATE, n_jobs=n_jobs, **params)


def _result_row(name: str, n_features: int, result: dict, gain, kept) -> dict:
    return {
        "Configuration": name,
        "Features": n_features,
        "Accuracy": result["accuracy_mean"],
        "Macro F1": result["macro_f1_mean"],
        "Std": result["macro_f1_std"],
        "Gain": gain,
        "Kept": kept,
    }


def screen_groups(X_train: pd.DataFrame, y_train: pd.Series):
    """5-fold CV of the baseline and of the baseline plus each group (XGBoost).

    A group is kept if the mean macro F1 improves by at least MIN_GAIN and by
    more than the standard deviation of the baseline folds.
    """
    y_zero_based = y_train - 1  # XGBoost needs labels 0..6; macro F1 is unaffected
    baseline = evaluate_model(build_xgboost(), X_train, y_zero_based)
    rows = [_result_row("baseline", X_train.shape[1], baseline, None, None)]
    kept = []
    for name in FEATURE_GROUPS:
        print(f"  evaluating {name} ...", flush=True)
        X_group = add_features(X_train, [name])
        result = evaluate_model(build_xgboost(), X_group, y_zero_based)
        gain = result["macro_f1_mean"] - baseline["macro_f1_mean"]
        is_kept = gain >= MIN_GAIN and gain > baseline["macro_f1_std"]
        if is_kept:
            kept.append(name)
        rows.append(_result_row(name, X_group.shape[1], result, gain, "yes" if is_kept else "no"))

    print("  evaluating all groups ...", flush=True)
    X_all = add_features(X_train)
    result = evaluate_model(build_xgboost(), X_all, y_zero_based)
    gain = result["macro_f1_mean"] - baseline["macro_f1_mean"]
    rows.append(_result_row("all groups", X_all.shape[1], result, gain, "-"))
    return pd.DataFrame(rows), kept


def rank_features(X_train: pd.DataFrame, y_train: pd.Series) -> pd.Series:
    """XGBoost gain importance fitted on the training partition only."""
    model = build_xgboost(n_jobs=-1, importance_type="gain").fit(X_train, y_train - 1)
    return pd.Series(model.feature_importances_, index=X_train.columns).sort_values(
        ascending=False
    )


def top_columns(X: pd.DataFrame, ranking: pd.Series, size: int) -> list:
    """The `size` most important columns, in their original order."""
    selected = set(ranking.index[:size])
    return [column for column in X.columns if column in selected]


def compare_subsets(X_train, y_train, X_val, y_val, ranking, top_k=TOP_K):
    """Fit on training, score on validation: top-k subsets against the full set.

    Returns the table and the size of the smallest subset whose macro F1 is
    within SUBSET_TOLERANCE of the full set.
    """
    sizes = sorted({k for k in top_k if k < len(ranking)}) + [len(ranking)]
    rows = []
    for size in sizes:
        columns = top_columns(X_train, ranking, size)
        model = build_xgboost(n_jobs=-1).fit(X_train[columns], y_train - 1)
        predictions = model.predict(X_val[columns]) + 1  # back to Cover_Type 1..7
        rows.append(
            {
                "Features": size,
                "Accuracy": accuracy_score(y_val, predictions),
                "Macro F1": f1_score(y_val, predictions, average="macro"),
            }
        )
    table = pd.DataFrame(rows)
    full = table["Macro F1"].iloc[-1]
    chosen = int(table.loc[table["Macro F1"] >= full - SUBSET_TOLERANCE, "Features"].min())
    return table, chosen


def confirm_with_other_folds(X_baseline, X_final, y_train) -> pd.DataFrame:
    """Baseline against the final set again, with a different CV seed (XGBoost).

    Checks that the result does not depend on one particular fold assignment.
    """
    y_zero_based = y_train - 1  # XGBoost needs labels 0..6; macro F1 is unaffected
    rows = []
    for name, X in (("baseline", X_baseline), ("final set", X_final)):
        print(f"  evaluating {name} ...", flush=True)
        result = evaluate_model(build_xgboost(), X, y_zero_based, random_state=CONFIRM_SEED)
        rows.append(_result_row(name, X.shape[1], result, None, None))
    table = pd.DataFrame(rows)
    table["Gain"] = table["Macro F1"] - table["Macro F1"].iloc[0]
    return table[["Configuration", "Features", "Accuracy", "Macro F1", "Std", "Gain"]]


def holdout_check(X_train, y_train, X_val, y_val, final_columns, groups):
    """Fit on training, score on validation: raw features against the final set.

    The groups were chosen with cross-validation on the training partition, so
    the validation partition gives an independent measurement of their impact.
    Returns an overall table and the F1 per class.
    """
    X_train_final = add_features(X_train, groups)[final_columns]
    X_val_final = add_features(X_val, groups)[final_columns]
    classes = sorted(y_val.unique())
    rows, per_class = [], {}
    for name, X_fit, X_score in (
        ("baseline", X_train, X_val),
        ("final set", X_train_final, X_val_final),
    ):
        model = build_xgboost(n_jobs=-1).fit(X_fit, y_train - 1)
        predictions = model.predict(X_score) + 1  # back to Cover_Type 1..7
        rows.append(
            {
                "Configuration": name,
                "Features": X_fit.shape[1],
                "Accuracy": accuracy_score(y_val, predictions),
                "Macro F1": f1_score(y_val, predictions, average="macro"),
            }
        )
        per_class[name] = f1_score(y_val, predictions, average=None, labels=classes)
    table = pd.DataFrame(rows)
    table["Gain"] = table["Macro F1"] - table["Macro F1"].iloc[0]
    per_class = pd.DataFrame(per_class, index=classes)
    per_class["Gain"] = per_class["final set"] - per_class["baseline"]
    return table, per_class


def main() -> None:
    start = time.perf_counter()
    df = clean(load_raw())
    X, y = df[FEATURES], df[TARGET]
    # The test partition is not used in this ticket.
    X_train, X_val, _, y_train, y_val, _ = split_train_val_test(X, y)

    print(
        f"scikit-learn {sklearn.__version__}, xgboost {xgboost.__version__}, "
        f"pandas {pd.__version__}"
    )
    print(f"Train rows: {len(X_train):,}  Validation rows: {len(X_val):,}")

    print("\n== 1. Screening: baseline vs baseline + group (XGBoost, 5-fold CV on train) ==")
    screening, kept = screen_groups(X_train, y_train)
    print(screening.round(4).to_string(index=False, na_rep="-"))
    print(f"Groups kept (gain >= {MIN_GAIN} and above the baseline std): {kept or 'none'}")

    X_train_kept = add_features(X_train, kept)
    X_val_kept = add_features(X_val, kept)

    print("\n== 2. Gain importance (XGBoost fitted on train), top 15 ==")
    ranking = rank_features(X_train_kept, y_train)
    share = (ranking / ranking.sum() * 100).round(2).rename("gain_share_pct")
    print(share.head(15).to_string())
    print(f"Features with zero gain: {int((ranking == 0).sum())}")

    print("\n== 3. Subsets: fit on train, score on validation ==")
    subsets, chosen = compare_subsets(X_train_kept, y_train, X_val_kept, y_val, ranking)
    print(subsets.round(4).to_string(index=False))
    print(f"Smallest subset within {SUBSET_TOLERANCE} of the full set: {chosen} features")

    final_columns = top_columns(X_train_kept, ranking, chosen)
    engineered = [c for c in final_columns if c not in FEATURES]
    print(f"Engineered features in the final set: {engineered or 'none'}")

    print("\n== 4. Confirmation: same comparison with another CV seed ==")
    confirmation = confirm_with_other_folds(X_train, X_train_kept[final_columns], y_train)
    print(confirmation.round(4).to_string(index=False))

    print("\n== 5. Held-out check on the validation partition (fit on train) ==")
    holdout, per_class = holdout_check(X_train, y_train, X_val, y_val, final_columns, kept)
    print(holdout.round(4).to_string(index=False))
    print("\nF1 per class (Cover_Type):")
    print(per_class.round(4).to_string())

    print(f"\nElapsed: {(time.perf_counter() - start) / 60:.1f} min")


if __name__ == "__main__":
    main()