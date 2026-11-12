# Spec: feature/16-m3-stratified-trainvalidationtest-split-stratifiedkfold

| | |
|---|---|
| Issue | #16 - [M3] Stratified train/validation/test split (StratifiedKFold) |
| Milestone | M3 |
| Branch | `feature/16-m3-stratified-trainvalidationtest-split-stratifiedkfold` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | #12 (missing values and duplicates, merged) |

## Goal

Provide the canonical stratified train/validation/test split that preserves the
class proportions of `Cover_Type` in every partition, with a fixed seed, so the
whole team uses the same partitions.

## Scope

- In scope: `src/data_split.py` (split + stratification check), documentation
  in `docs/PREPROCESSING.md`.
- Out of scope: scaling (#14), outliers (#13), the baseline and cross-validation
  protocol (#19), any model training.

## Design

| File | Change |
|---|---|
| `src/data_split.py` | New. `split_train_val_test()`, `class_shares()`, `check_stratification()`, `main()`. |
| `docs/PREPROCESSING.md` | New section *Train/validation/test split*. |

Decisions:

- **Ratios 70 / 15 / 15** (train / validation / test). With 581,012 rows, 15%
  test ≈ 87k rows is enough to reliably measure the rarest class
  (Cottonwood/Willow, 0.47% ≈ 410 rows in test); 70% train ≈ 406k rows is ample
  for training.
- **Stratified on `Cover_Type`**, so every partition keeps the class shares.
- **`random_state=42`** for reproducible partitions.
- **Test first, then validation from the remainder**, so the three partitions
  never overlap.
- **No leakage**: the split happens before any fitted step; `data_split.py`
  fits nothing.
- Reuses `load_raw` (`data_audit`) and `clean`, `FEATURES`, `TARGET`
  (`data_cleaning`).

## Acceptance criteria

- [x] Define split ratios (train/val/test)
- [x] Use stratified split to keep class proportions
- [x] Seed for reproducibility
- [x] Document split sizes
- [x] Stratified split done with fixed seed
- [x] Class proportions preserved across splits

## Verification

Run on 2026-11-12 with `python src/data_split.py`:

| Check | Result |
|---|---|
| Split sizes (train / validation / test) | 406,708 / 87,152 / 87,152 (70% / 15% / 15%) |
| `check_stratification()` | Passed |
| Class-share deviation per partition | < 0.001 percentage points |
