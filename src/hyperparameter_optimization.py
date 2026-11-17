"""Hyperparameter optimization of the shortlisted models (ticket #29).

Tunes Random Forest (primary) and XGBoost (secondary) with `RandomizedSearchCV`
under the shared CV protocol (`StratifiedKFold(n_splits=5, shuffle=True,
random_state=42)`, macro F1 the main metric) and compares the tuned models
against the defaults recorded in #23, all on the canonical train split.
"""
import sys

from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold

from baseline import MACRO_F1, N_SPLITS, RANDOM_STATE, evaluate_model
from data_audit import load_raw
from data_cleaning import FEATURES, TARGET, clean
from data_split import split_train_val_test
from gradient_boosting import build_models
from model_comparison import LabelOffsetClassifier
from random_forest import build_model

RF_N_ITER = 10
XGB_N_ITER = 30

CV = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)


def rf_search_space() -> dict:
    """Hyperparameter distributions for Random Forest.

    The space targets the dimensions that matter most for this dataset: tree
    depth and the leaf / split regularization (the forest runs without a depth
    limit by default, see #28), the number of trees, and the features
    considered per split.
    """
    return {
        "n_estimators": [100, 200, 300, 400],
        "max_depth": [None, 10, 20, 30, 40, 50],
        "min_samples_leaf": [1, 2, 4, 8],
        "min_samples_split": [2, 5, 10, 20],
        "max_features": ["sqrt", "log2", None],
    }


def xgb_search_space() -> dict:
    """Hyperparameter distributions for XGBoost."""
    return {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 6, 9, 12],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "subsample": [0.6, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0],
        "min_child_weight": [1, 3, 5],
        "reg_lambda": [0.0, 1.0, 10.0],
        "reg_alpha": [0.0, 1.0, 10.0],
    }


def tune_random_forest(X, y, n_iter=RF_N_ITER):
    """Randomized search over Random Forest hyperparameters.

    `y` is Cover_Type (1..7). Returns the fitted `RandomizedSearchCV`; its
    `best_estimator_` is refit on the full `X` / `y`.
    """
    # Single-threaded estimator: RandomizedSearchCV parallelizes over candidates
    # (n_jobs=-1), so a nested n_jobs=-1 would oversubscribe the cores.
    model = build_model().set_params(n_jobs=1)
    search = RandomizedSearchCV(
        model,
        rf_search_space(),
        n_iter=n_iter,
        scoring=MACRO_F1,
        cv=CV,
        n_jobs=-1,
        random_state=RANDOM_STATE,
        refit=True,
        verbose=1,
    )
    search.fit(X, y)
    return search


def tune_xgboost(X, y, n_iter=XGB_N_ITER):
    """Randomized search over XGBoost hyperparameters.

    XGBoost 2.1 requires 0-indexed labels, so this fits on `y - 1`; macro F1 is
    invariant to the label offset, so the best parameters are identical to
    tuning on `y`. The returned search is fitted on 0-indexed labels — wrap its
    `best_estimator_` in `LabelOffsetClassifier` to score on 1..7.
    """
    # Single-threaded estimator for the same reason as Random Forest above.
    model = build_models()["XGBoost"].set_params(n_jobs=1)
    search = RandomizedSearchCV(
        model,
        xgb_search_space(),
        n_iter=n_iter,
        scoring=MACRO_F1,
        cv=CV,
        n_jobs=-1,
        random_state=RANDOM_STATE,
        refit=True,
        verbose=1,
    )
    search.fit(X, y - 1)
    return search


def evaluate_defaults(X, y) -> dict:
    """Re-evaluate the #23 defaults with the shared protocol."""
    return {
        "RandomForest": evaluate_model(build_model(), X, y),
        "XGBoost": evaluate_model(
            LabelOffsetClassifier(build_models()["XGBoost"]), X, y
        ),
    }


def main() -> None:
    rf_n_iter, xgb_n_iter = RF_N_ITER, XGB_N_ITER
    if len(sys.argv) > 1:
        rf_n_iter = int(sys.argv[1])
    if len(sys.argv) > 2:
        xgb_n_iter = int(sys.argv[2])

    df = clean(load_raw())
    X_train, _, _, y_train, _, _ = split_train_val_test(df[FEATURES], df[TARGET])

    print(
        f"== Hyperparameter optimization (RandomizedSearchCV, stratified "
        f"{N_SPLITS}-fold CV on {len(y_train):,} training rows, macro F1) =="
    )

    print("\n-- Defaults (#23, shared protocol) --", flush=True)
    defaults = evaluate_defaults(X_train, y_train)
    for name in ("RandomForest", "XGBoost"):
        d = defaults[name]
        print(
            f"{name}: macro F1 {d['macro_f1_mean']:.4f} ± {d['macro_f1_std']:.4f}"
        )

    tuned = {}

    print(f"\n-- Random Forest ({rf_n_iter} iterations) --", flush=True)
    rf_search = tune_random_forest(X_train, y_train, n_iter=rf_n_iter)
    tuned["RandomForest"] = {
        "best_params": rf_search.best_params_,
        "best_cv": rf_search.best_score_,
        "scores": evaluate_model(rf_search.best_estimator_, X_train, y_train),
    }
    print(f"Best params: {rf_search.best_params_}")
    print(f"Best CV macro F1 (search): {rf_search.best_score_:.4f}")

    print(f"\n-- XGBoost ({xgb_n_iter} iterations) --", flush=True)
    xgb_search = tune_xgboost(X_train, y_train, n_iter=xgb_n_iter)
    tuned["XGBoost"] = {
        "best_params": xgb_search.best_params_,
        "best_cv": xgb_search.best_score_,
        "scores": evaluate_model(
            LabelOffsetClassifier(xgb_search.best_estimator_), X_train, y_train
        ),
    }
    print(f"Best params: {xgb_search.best_params_}")
    print(f"Best CV macro F1 (search): {xgb_search.best_score_:.4f}")

    print("\n== Default vs tuned (5-fold CV, macro F1) ==")
    for name in ("RandomForest", "XGBoost"):
        d = defaults[name]
        s = tuned[name]["scores"]
        print(
            f"{name}: default {d['macro_f1_mean']:.4f} ± {d['macro_f1_std']:.4f}  ->  "
            f"tuned {s['macro_f1_mean']:.4f} ± {s['macro_f1_std']:.4f}"
        )


if __name__ == "__main__":
    main()
