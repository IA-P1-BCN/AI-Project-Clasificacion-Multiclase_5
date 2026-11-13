# Spec: feature/9-class-eda

| | |
|---|---|
| Issue | #9 - [M2] Classification-specific EDA (histograms per class, correlation matrix) |
| Milestone | M2 |
| Branch | `feature/9-class-eda` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | #7 (audit) |

> Written retroactively (ticket #9 was merged in PR #58 before the spec-driven
> workflow of PR #63 existed). It records what was built and verified.

## Goal

Explore the features with visualizations suited to classification
(distributions per class and correlations) and identify which features
separate the classes.

## Scope

- In scope: histograms and boxplots per class for the numeric features, a
  correlation matrix, a ranking of class separation (eta squared) and the
  figures saved for the report.
- Out of scope: skewness, outliers and PCA (#10), analysis of the 44 binary
  indicators against the class, and any transformation.

## Design

| File | Change |
|---|---|
| `src/class_eda.py` | New. Per-class histograms and boxplots, correlation matrix, eta squared ranking. Saves `class_histograms.png`, `class_boxplots.png` and `correlation_matrix.png` in `docs/figures/`. |
| `docs/EDA.md` | *Feature analysis* section: distributions per class, correlation matrix, features that separate the classes. |

Decision: eta squared (share of a feature's variance explained by the class)
ranks the numeric features. It only captures differences between class means,
and the limitation is stated in the documentation.

## Acceptance criteria

- [x] Histograms per class and a correlation matrix are produced
- [x] Plots are committed for the report (`docs/figures/`)

## Verification

```bash
python src/class_eda.py
```

Expected: `Elevation` is the most discriminative feature (eta squared 0.616),
followed by `Horizontal_Distance_To_Roadways` (0.096), `Slope` (0.074) and
`Horizontal_Distance_To_Fire_Points` (0.070). No pair of features reaches 0.8 in
absolute correlation (largest: `Hillshade_9am` / `Hillshade_3pm`, -0.78).
