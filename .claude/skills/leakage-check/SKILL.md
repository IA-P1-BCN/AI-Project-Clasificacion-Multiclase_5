---
name: leakage-check
description: Checklist to verify that a preprocessing, training or evaluation change does not leak validation or test data into training. Use before committing any change that fits something on data.
---

# Leakage check

Run through every item; each one needs evidence (a line of code or a command
output), not an assumption.

## Static checks

- [ ] Every `fit`, `fit_transform` and `fit_resample` receives training rows only.
- [ ] The split happens before any fitted step, and is stratified on `Cover_Type`.
- [ ] Fitted steps are inside a scikit-learn `Pipeline` when cross-validation
      is used, so they are refitted on each training fold.
- [ ] No statistic of the full dataset (mean, quantile, class frequency) is
      used to transform features.
- [ ] Resampling and class weighting use training rows only.
- [ ] The test set is not used to choose a model, a scaler or a hyperparameter.

Useful search: `git diff develop...HEAD | grep -nE "fit(_transform|_resample)?\("`

## Dynamic checks

- [ ] The fitted parameters equal the training statistics and differ from the
      full-data statistics, e.g. for a `StandardScaler`:
      `scaler.mean_ == X_train[NUMERIC_FEATURES].mean()`.
- [ ] After transforming, training numeric features have mean about 0 and
      standard deviation about 1; validation and test are close but not exact.
- [ ] Binary features and the target are identical before and after.

## Report

State which items passed, with the evidence, and which could not be checked.
