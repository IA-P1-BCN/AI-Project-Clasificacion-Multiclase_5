# Dataset selection

Decision record for milestone M1, issue #3. Chooses the definitive dataset for
the project from the three suggested candidates and justifies the choice on
size, number of classes, class balance, feature types and availability.

## Candidates

All three are open datasets from the UCI Machine Learning Repository and satisfy
the basic requirement of multiclass classification (>= 3 classes).

| Dataset | UCI id | Rows | Features | Feature types | Classes | Class balance | Missing values |
|---|---|---|---|---|---|---|---|
| Wine | 109 | 178 | 13 | all numeric (chemical analysis) | 3 (cultivars) | near balanced (59 / 71 / 48) | none |
| Dry Bean | 602 | 13,611 | 16 | all numeric (geometric shape) | 7 (bean varieties) | moderate (~1:7) | none |
| **Forest Cover Type (Covertype)** | **31** | **581,012** | **54** | **10 numeric + 44 binary one-hot** | **7 (tree cover types)** | **strong (~1:103)** | **none** |

Covertype's 44 binary features are 4 `Wilderness_Area` indicators and 40
`Soil_Type` indicators, already one-hot encoded in the raw file. See
[../specs/ontology.md](../specs/ontology.md) for the full feature and class list.

## Decision

**Selected: Forest Cover Type (Covertype), UCI dataset 31.**

## Justification

- **Size.** 581,012 observations give a realistic, large-scale problem: a
  meaningful stratified train/validation/test split, room for cross-validation,
  and a genuine incentive to think about compute cost and efficiency. Wine (178
  rows) is too small to produce a convincing evaluation; Dry Bean (13,611) is
  adequate but modest.
- **Number of classes.** 7 classes, well above the >= 3 requirement. Dry Bean
  also has 7; Wine only 3.
- **Class balance.** Covertype is strongly imbalanced (minority class
  Cottonwood/Willow 0.47% vs. majority Lodgepole Pine 48.76%, about 1:103). This
  is the most valuable property for the project: it forces stratified splits,
  macro F1 and per-class metrics instead of plain accuracy, and makes resampling
  and class weighting meaningful. Wine and Dry Bean are close to balanced and
  would make the task too easy for the target delivery level.
- **Feature types.** The mix of 10 quantitative numeric features and 44 binary
  one-hot features requires a proper `ColumnTransformer` / `Pipeline` that scales
  only the numeric features, and enforces leakage discipline (fit on training
  data only). Wine and Dry Bean are all-numeric and exercise far less of the
  preprocessing work the course asks for.
- **Real-world relevance.** The dataset predicts the dominant tree cover type of
  30 x 30 m cells in the Roosevelt National Forest (Colorado) from cartographic
  variables, a tangible ecological / land-management problem.
- **Availability.** All three are freely available on UCI. Covertype is a
  well-documented, widely used benchmark, which eases comparison with published
  results.

**Trade-off.** Covertype's size and imbalance make it harder than the
alternatives (more compute, more careful metric choices), but that difficulty is
exactly what the project's "Medio" and higher delivery levels require.

This decision matches the rest of the repository, which is already built on
Covertype.

## Reproducing the candidate facts

The numbers above come from each dataset's UCI page:

- Wine: <https://archive.ics.uci.edu/dataset/109/wine>
- Dry Bean: <https://archive.ics.uci.edu/dataset/602/dry+bean+dataset>
- Forest Cover Type (Covertype): <https://archive.ics.uci.edu/dataset/31/covertype>

Covertype's shape and class shares are verified locally once the raw file is in
place:

```bash
python src/data_audit.py
```
