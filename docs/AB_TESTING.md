# A/B testing between models

Issue #52 (optional, `Could`). Spec: [specs/feature-52-m8-ab-testing-between-models.md](../specs/feature-52-m8-ab-testing-between-models.md).

Two models are served by the same API at the same time. Each request is sent to one of them at random, the feedback collected in #35 gives the accuracy of each variant, and a statistical rule decides whether there is a winner.

## Contents

- [Variants](#variants)
- [How it works](#how-it-works)
- [Decision rule](#decision-rule)
- [Running the test](#running-the-test)
- [Results](#results)
- [Reading the results](#reading-the-results)
- [Limitations](#limitations)
- [Reproduction](#reproduction)

## Variants

| | A (control) | B (challenger) |
|---|---|---|
| Model | Random Forest, 100 trees, untuned (#32) | XGBoost tuned in #29 |
| Version | 0.1.0 | 0.2.0 |
| File | `models/model.joblib` (136.3 MB) | `models/model_b.joblib` (19.6 MB) |
| Export | `python src/export_model.py` | `python src/export_challenger.py` |
| Validation accuracy | 0.9520 | 0.9471 |
| Validation macro F1 | 0.9186 | 0.9244 |

B uses the best parameters found in #29: `learning_rate=0.05, n_estimators=300, max_depth=12, subsample=0.8, colsample_bytree=0.8, min_child_weight=3, reg_lambda=0.0, reg_alpha=1.0`. It is fitted on the train split only and keeps the serving contract of the main model (54 raw `FEATURES` in, `predict_proba` and `classes_` 1-7 out), so the API loads both files with the same code. The test set is not used by either model.

## How it works

- **Traffic split.** `AB_TRAFFIC_B` (0 to 1, default `0`) is the share of `POST /predict` requests sent to B. With `0` the test is off and every request goes to A. If B cannot be loaded, every request goes to A and `GET /health` reports it under `ab_test`.
- **Forcing a variant.** `POST /predict?variant=A` or `?variant=B` skips the split (used by tests and the simulation). Any other value gives HTTP 422.
- **Storage.** Every prediction is stored with its `variant` (`A` or `B`) and the `model_version` of the model that served it. Tables created before #52 are migrated automatically: the column is added and the old rows are marked `A`.
- **Results.** `GET /ab/results` returns, per variant, the predictions served, the feedback received, how many were correct, the live accuracy and the mean confidence, followed by the decision (`decision`, `difference` = B minus A, `z`, `p_value`) and the `rule` that was applied. Feedback comes from `POST /feedback` (#35).

## Decision rule

| Step | Condition | Outcome |
|---|---|---|
| 1 | Fewer than 200 feedback entries in either variant | `insufficient_data` |
| 2 | Two-sided two-proportion z-test on the accuracies, `p < 0.05` **and** `|B - A| >= 0.5` accuracy points | `winner_A` or `winner_B` (the more accurate one) |
| 3 | Otherwise | `inconclusive` |

The minimum difference keeps a gap that is statistically significant but too small to matter from being declared a win. The thresholds are constants in [src/ab_testing.py](../src/ab_testing.py) (`MIN_FEEDBACK_PER_VARIANT`, `ALPHA`, `MIN_EFFECT`).

## Running the test

```bash
# 1. Export the challenger with the pinned versions (inside Docker)
docker compose run --rm --no-deps app python src/export_challenger.py

# 2. Send half of the traffic to B and reload the API (it loads the models at startup)
AB_TRAFFIC_B=0.5 docker compose up -d api      # PowerShell: $env:AB_TRAFFIC_B = "0.5"; docker compose up -d api

# 3. Use the API normally (POST /predict, then POST /feedback), and read the results
curl http://localhost:8000/ab/results
```

To switch the test off, unset `AB_TRAFFIC_B` (or set it to `0`) and run `docker compose up -d api` again.

## Results

All numbers come from `python src/ab_simulation.py` (seed 42, validation set), run inside Docker.

### Offline comparison on the whole validation set (87,152 rows)

| Model | Accuracy | Macro F1 |
|---|---|---|
| A (Random Forest 0.1.0) | **0.9520** | 0.9186 |
| B (XGBoost 0.2.0) | 0.9471 | **0.9244** |

Rows only A gets right: 1,621. Rows only B gets right: 1,188. McNemar test: chi-square 66.44, p = 3.6e-16, so A is more accurate. B has the higher macro F1.

### Simulated A/B test (50 % of the traffic to B)

| Requests | Variant | Feedback | Correct | Accuracy | Mean confidence |
|---|---|---|---|---|---|
| 10,000 | A | 5,010 | 4,767 | 0.9515 | 0.8755 |
| 10,000 | B | 4,990 | 4,709 | 0.9437 | 0.8928 |
| 60,000 | A | 29,958 | 28,557 | 0.9532 | 0.8772 |
| 60,000 | B | 30,042 | 28,438 | 0.9466 | 0.8937 |

| Requests | B - A | z | p-value | Decision |
|---|---|---|---|---|
| 10,000 | -0.78 points | -1.752 | 0.0797 | `inconclusive` |
| 60,000 | -0.66 points | -3.721 | 0.0002 | **`winner_A`** |

### A/A control (B serves the same model as A)

| Requests | B - A | z | p-value | Decision |
|---|---|---|---|---|
| 10,000 | -0.20 points | -0.461 | 0.6451 | `inconclusive` |
| 60,000 | -0.25 points | -1.450 | 0.1470 | `inconclusive` |

When both variants are the same model the rule declares no winner, as it should.

### Check against the running API

With `AB_TRAFFIC_B=0.5` in Docker (MySQL), 40 identical `POST /predict` requests were served 24 by A and 16 by B. After sending feedback for all of them, `GET /ab/results` counted them per variant and answered `insufficient_data`, as the 200-feedback minimum was not reached. `?variant=B` returned `B`, `?variant=C` returned 422, and a prediction stored before the migration appeared under variant A.

## Reading the results

- **By the documented rule, A wins**: it is 0.66 accuracy points better over 60,000 simulated requests, which is significant (p = 0.0002) and above the 0.5-point minimum. The offline comparison on all 87,152 rows agrees (0.49 points).
- **B has the better macro F1** (0.9244 against 0.9186), which is the main metric of the project. The rule decides by accuracy because accuracy is what the feedback of each request measures directly. The result is therefore a verdict on accuracy, not on macro F1.
- **Sample size matters.** With 10,000 requests (about 5,000 labelled per variant) a real gap of about half a point is not detectable (p = 0.08). Detecting 0.5 points at about 95 % accuracy with 80 % power needs about 30,000 labelled predictions per variant, which is why the 60,000-request run reaches a decision and the 10,000-request one does not.

## Limitations

- The simulation uses the true label of every row as feedback. In production feedback is partial and may be biased (people may report mostly errors), so the real test needs more traffic and its accuracy would not be comparable with the offline one.
- Requests carry no user id, so a user can be served by A and B in turn. Sticky assignment per user is out of scope.
- There is no live macro F1 per variant. If macro F1 is the criterion, it would have to be computed from the per-class feedback of each variant (not implemented).
- The decision rule is evaluated whenever `GET /ab/results` is called: checking it repeatedly during the test and stopping at the first significant result inflates the false-positive rate. Fix the sample size beforehand.
- Only two variants and a fixed split; no bandit-style adaptation.

## Reproduction

```bash
python -m pytest tests/test_ab_testing.py    # variant split, z-test, decision, storage, migration

docker compose run --rm --no-deps app python src/export_challenger.py
docker compose run --rm --no-deps app python src/ab_simulation.py            # 10,000 requests
docker compose run --rm --no-deps app python src/ab_simulation.py 60000      # 60,000 requests
```

`ab_simulation.py` takes `[n_requests] [share_b] [seed]` and needs both exported models. Run it with the pinned versions (Docker): a model pickled with another scikit-learn version does not load (see the guide, D10.5).