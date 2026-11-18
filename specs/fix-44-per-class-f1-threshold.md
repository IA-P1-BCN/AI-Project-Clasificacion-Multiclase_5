# Spec: fix/44-per-class-f1-threshold

| | |
|---|---|
| Issue | Follow-up to #44 (no dedicated issue); defect found while reviewing the merged report |
| Milestone | M7 |
| Branch | `fix/44-per-class-f1-threshold` (from `develop`) |
| Owner | @carovasq |
| Depends on | #44 (merged via PR #108) |

## Goal

Fix a factual defect in `docs/TECHNICAL_REPORT.md`: the prose claims every class
exceeds F1 **0.87** on test, but the per-class table in the same document reports
Aspen at **0.8410**. The table is correct and stays untouched; the two prose
claims derived from it are corrected to match.

## Scope

- In scope: the two sentences in `docs/TECHNICAL_REPORT.md` that state the
  per-class F1 floor (results section and conclusions section).
- Out of scope: every metric, table and figure in the report (all verified
  correct), `docs/MODELING.md` (checked — it does not state a per-class floor),
  and any code or model change. No model is re-run and no number is recomputed.

## Design

| File | Change |
|---|---|
| `docs/TECHNICAL_REPORT.md` | (1) Results prose: "Every class exceeds F1 0.87" → "Every class exceeds F1 0.84, the lowest being Aspen (0.8410)", and Aspen's high precision is given explicitly (0.948) so the precision/recall asymmetry is readable without going back to the table. (2) Conclusions bullet: "every F1 ≥ 0.87 on test" → "every F1 ≥ 0.84 on test, lowest Aspen 0.8410". |

Reasons:

- **The floor is set by Aspen, not by the second-worst class.** The per-class
  test table gives Aspen F1 0.8410 and Cottonwood/Willow 0.8767. A 0.87 floor
  would exclude Aspen, the one class the surrounding paragraph singles out as
  the hardest — the claim contradicted its own evidence.
- **Overstating the floor weakens the honest argument.** The point of the
  paragraph is that performance holds up across all seven classes under a
  ~1:103 imbalance. That argument survives at 0.84 and does not need 0.87; an
  inflated figure is the kind of detail a reviewer checks against the table.
- **Prose only.** Correcting the table instead would mean changing a number the
  evaluation script produced, which is the opposite of the fix.

## Acceptance criteria

- [x] The stated per-class F1 floor matches the minimum F1 in the per-class test
      table (0.8410, Aspen).
- [x] Both occurrences are corrected (results prose and conclusions bullet).
- [x] No table value, metric or decision changed.
- [x] No other document states a per-class F1 floor that is now inconsistent.

## Verification

- Per-class test table in `docs/TECHNICAL_REPORT.md` (line 225 onwards): minimum
  F1 is Aspen 0.8410, with precision 0.9480 and recall 0.7556; second lowest is
  Cottonwood/Willow 0.8767. The corrected prose matches all of these.
- `grep -rn "0\.87" docs/*.md README.md` — the remaining hits are unrelated
  table values in `MODELING.md`, `PREPROCESSING.md` and the model-comparison
  table; none is a per-class floor claim.
- `grep -rni "exceeds F1\|every F1\|F1 ≥" docs/*.md README.md` — the only two
  floor claims in the repository are the two corrected here.
- `git diff origin/develop...fix/44-per-class-f1-threshold` touches
  `docs/TECHNICAL_REPORT.md` only, 7 insertions and 6 deletions, all prose.

## Not verified

- The report was not regenerated from the evaluation scripts; this change trusts
  the committed per-class table as the source of truth, which is what the
  original defect failed to do.
