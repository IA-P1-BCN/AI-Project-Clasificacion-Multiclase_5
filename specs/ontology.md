# Ontology

Shared vocabulary of the project. Code, specs, docs and agents use these terms
and identifiers exactly as written here. If a concept is missing, add it in the
branch that introduces it.

## Domain

| Term | Definition |
|---|---|
| Covertype dataset | UCI dataset 31. Cartographic variables for 30 x 30 m cells of four wilderness areas in Roosevelt National Forest (Colorado). 581,012 rows, 54 features, 1 target. |
| Observation | One row: one 30 x 30 m cell. |
| Cover type | Dominant tree species of the cell. The target. |
| Wilderness area | One of four designated areas; one-hot encoded in the raw file. |
| Soil type | One of 40 soil types; one-hot encoded in the raw file. |

## Data entities

| Entity | Identifier | Definition |
|---|---|---|
| Raw dataset | `data/raw/covtype.data` | Original file, no header, comma separated. Immutable and git-ignored. |
| Processed dataset | `data/processed/` | Outputs derived from the raw dataset. Git-ignored. |
| Target | `Cover_Type` | Integer 1-7. |
| Numeric features | `NUMERIC_FEATURES` (`COLUMNS[:10]`) | The 10 quantitative features listed below. |
| Binary features | `BINARY_FEATURES` (`COLUMNS[10:54]`) | `Wilderness_Area1..4` and `Soil_Type1..40`, values 0/1. |
| Feature matrix | `X` | The 54 feature columns. |
| Target vector | `y` | The `Cover_Type` column. |

### Numeric features

| Column | Unit | Notes |
|---|---|---|
| `Elevation` | meters | Most discriminative feature (eta squared 0.616) |
| `Aspect` | degrees azimuth, 0-360 | Circular |
| `Slope` | degrees | |
| `Horizontal_Distance_To_Hydrology` | meters | Right-skewed |
| `Vertical_Distance_To_Hydrology` | meters | Can be negative; heaviest tails |
| `Horizontal_Distance_To_Roadways` | meters | |
| `Hillshade_9am` | index 0-255 | Left-skewed |
| `Hillshade_Noon` | index 0-255 | Left-skewed |
| `Hillshade_3pm` | index 0-255 | |
| `Horizontal_Distance_To_Fire_Points` | meters | Right-skewed |

### Target classes

| `Cover_Type` | Name | Share of rows |
|---|---|---|
| 1 | Spruce/Fir | 36.46% |
| 2 | Lodgepole Pine | 48.76% |
| 3 | Ponderosa Pine | 6.15% |
| 4 | Cottonwood/Willow | 0.47% |
| 5 | Aspen | 1.63% |
| 6 | Douglas-fir | 2.99% |
| 7 | Krummholz | 3.53% |

## Machine learning concepts

| Term | Definition in this project |
|---|---|
| Train / validation / test set | Stratified partitions of the dataset. The test set is used once, for the final evaluation. |
| Stratified split | Split that preserves the class proportions of `Cover_Type` in every partition. |
| Data leakage | Any use of validation or test rows to fit a transformation or a model. |
| Fit | Learning parameters from data (e.g. mean and standard deviation of a scaler). Only done on training data. |
| Transform | Applying already fitted parameters to any partition. |
| Preprocessor | A scikit-learn transformer (`ColumnTransformer`) that maps `X` to model-ready features. |
| Pipeline | scikit-learn `Pipeline` chaining the preprocessor and an estimator, so that cross-validation refits the preprocessor on each training fold. |
| Scaling | Rescaling numeric features to comparable ranges. Never applied to binary features or to the target. |
| Imbalance | Unequal class frequencies (min/max ratio about 1:103). |
| Macro F1 | Unweighted mean of per-class F1. Main comparison metric together with per-class metrics. |
| Overfitting gap | Training accuracy minus validation accuracy. Quality gate: below 5%. |
| Baseline | Simplest reference model that others must beat. |

## Process concepts

| Term | Definition |
|---|---|
| Milestone (M0-M8) | Project phase; every issue belongs to one. |
| Issue / ticket | Unit of work on GitHub, titled `[M#] <title>`, with tasks and acceptance criteria. |
| MoSCoW | Priority label: Must / Should / Could. |
| Level | Delivery level: Esencial / Medio / Avanzado / Experto. |
| Feature branch | `feature/<issue-number>-<short-description>`, created from `develop`. |
| Spec | `specs/<branch-name-with-dashes>.md`: what a branch will deliver and how it is verified. |
| Acceptance criteria | Checklist from the issue that defines "done". |
| Subagent | Specialized agent definition in `.claude/agents/`. |
| Skill | Reusable procedure in `.claude/skills/<name>/SKILL.md`. |

## Relationships

```
Milestone 1 ──< Issue 1 ──1 Feature branch 1 ──1 Spec
Raw dataset ──> X (NUMERIC_FEATURES + BINARY_FEATURES) + y (Cover_Type)
X_train ──fit──> Preprocessor ──transform──> X_train, X_validation, X_test
Pipeline = Preprocessor + Estimator
```
