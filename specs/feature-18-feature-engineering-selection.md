# Spec: feature/18-feature-engineering-selection

| | |
|---|---|
| Issue | #18 - [M3] Feature engineering / selection |
| Milestone | M3 |
| Branch | `feature/18-feature-engineering-selection` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | M2 EDA (done); #12 cleaning, #14 scaling, #16 split, #19 baseline protocol and #22 gradient boosting (all merged) |

## Goal

Create the candidate features suggested by the EDA, measure whether each one
improves a gradient-boosted model under the project's evaluation protocol, keep
only those that help, and document the impact.

## Scope

- In scope: candidate features (interactions, ratios, circular encoding,
  one-hot to id), importance and selection analysis, a before/after comparison
  and a section in `docs/PREPROCESSING.md`.
- Out of scope:
  - Hyperparameter tuning (M4).
  - Changes to feature scaling (#14) and outlier handling (#13). If an
    engineered feature is kept, scaling it for linear models belongs to #14.
  - Exporting the pipeline for the app (#32).
  - Final evaluation on the test partition (M5).

## Design

| File | Change |
|---|---|
| `src/feature_engineering.py` | New. `add_features(X, groups)` (pure, stateless), a transformer wrapper for `Pipeline`, importance ranking, the comparison experiment and `main()`. |
| `docs/PREPROCESSING.md` | New section *Feature engineering and selection* with the results and the command that reproduces them. |

No new dependency.

### Candidate groups

| Group | Features | Evidence |
|---|---|---|
| `aspect_circular` | `Aspect_sin`, `Aspect_cos` | `Aspect` is an angle (circular, see EDA) |
| `hydrology_distance` | `Hydrology_Euclidean` = sqrt(H^2 + V^2) | Horizontal and vertical distances to hydrology are correlated (r = 0.606) |
| `hydrology_ratio` | `Hydrology_Slope_Ratio` = V / (H + 1) | The issue asks for ratios; 24,603 rows have H = 0, hence the + 1 |
| `elevation_offsets` | `Elevation_minus_VDH`, `Elevation_minus_HDH` | `Elevation` dominates (eta squared 0.616) and all three are in meters |
| `distance_combinations` | Sum and absolute difference of each pair of the three horizontal distances (6 features) | `Horizontal_Distance_To_Roadways` and `..._Fire_Points` are the next best separators |
| `category_ids` | `Wilderness_Area_id`, `Soil_Type_id` | Exactly one indicator is active per row (#12); useful for tree models only |

H = `Horizontal_Distance_To_Hydrology`, V = `Vertical_Distance_To_Hydrology`.

### Evaluation protocol

1. Clean with `clean()` and split with `split_train_val_test()` (#16). The test
   partition is never used in this branch.
2. Screening: LightGBM (`random_state=42`), 5-fold stratified CV on the training
   partition through `evaluate_model()` (#19). Compare the 54 raw features
   (baseline) with the baseline plus each group, and plus all groups.
3. A group is kept if the mean macro F1 improves by at least 0.002 and by more
   than the standard deviation of the baseline folds.
4. Selection: rank the kept feature set by LightGBM gain importance fitted on
   the training partition, then compare the full set with the top-k subsets
   (k = 20, 30, 40) on the validation partition. Keep the smallest subset whose
   validation macro F1 is within 0.001 of the full set.
5. Confirmation: XGBoost on the final feature set against the baseline (CV on
   the training partition), to check that the gain is not specific to LightGBM.

### Leakage

The candidate features are computed row by row and fit nothing. Importance
rankings are fitted on the training partition only, subsets are compared on the
validation partition, and the test partition is untouched (skill `leakage-check`).

## Acceptance criteria

- [ ] Feature engineering documented with impact (only if time allows)
- [ ] Candidate features generated (interactions, ratios) from the groups above
- [ ] Feature importance / selection evaluated on training data only
- [ ] Only features that help are kept, with the decision rule applied and recorded
- [ ] Before/after macro F1 table in `docs/PREPROCESSING.md`, with the reproduction command
- [ ] `leakage-check` passed; the test partition is not used

## Verification

- `python src/feature_engineering.py` prints the screening table, the
  importance ranking, the subset comparison and the final feature set.
- Tick the criteria only after running the command and recording the observed results.