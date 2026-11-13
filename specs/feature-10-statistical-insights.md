# Spec: feature/10-statistical-insights

| | |
|---|---|
| Issue | #10 - [M2] Deeper statistical insights |
| Milestone | M2 |
| Branch | `feature/10-statistical-insights` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | #9 (class EDA) |

> Written retroactively (ticket #10 was merged in PR #59 before the spec-driven
> workflow of PR #63 existed). It records what was built and verified.

## Goal

Add optional extra analysis to strengthen the EDA: feature distributions,
outliers and pairwise relationships, and note insights for feature engineering.

## Scope

- In scope: skewness, excess kurtosis and the 1.5 x IQR rule per numeric
  feature, a pairplot of the top features, a PCA projection and a list of
  feature engineering candidates.
- Out of scope: removing outliers (#13), applying transformations (#14) and
  building the new features (#18).

## Design

| File | Change |
|---|---|
| `src/statistical_insights.py` | New. Statistics over all rows; the pairplot and the PCA scatter use a balanced sample (1,000 rows per class) for visualization only. Saves `feature_distributions.png`, `pairplot_top_features.png` and `pca_projection.png`. |
| `docs/EDA.md` | *Deeper statistical insights* section. |

Decisions: no formal normality test (with 581,012 rows it rejects normality for
any real data), and no outlier is removed (the IQR flags look like long tails
of skewed variables, not confirmed errors).

## Acceptance criteria

- [x] Feature distributions checked (skewness, kurtosis, IQR)
- [x] Pairwise relationships explored (pairplot, PCA projection)
- [x] Insights for feature engineering documented

## Verification

```bash
python src/statistical_insights.py
```

Expected: the strongest skew is `Vertical_Distance_To_Hydrology` (1.79,
kurtosis 5.25); the IQR rule flags up to 5.4% of rows; in the PCA of the 10
numeric features PC1 explains 25.9% and PC2 21.5% of the variance, and PC10
explains about 0% (an almost exact linear dependency, not verified).
