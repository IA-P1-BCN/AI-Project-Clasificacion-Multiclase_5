# Spec: docs/living-guide-levi-contributions

| | |
|---|---|
| Issue | none (living team guide update for #12, #14, #20, #24, #25, #32) |
| Milestone | M7 |
| Branch | `docs/living-guide-levi-contributions` (from `develop`) |
| Owner | @levifvy |
| Depends on | #12, #14, #20, #24, #32 (merged), #25 (PR open) |

## Goal

Document the decisions, justifications, plain-language explanations and
evidence of @levifvy's tickets (#12, #14, #20, #24, #25, #32) in the team's
living classification guide (`docs/GUIA_PROYECTO_CLASIFICACION.md`).

## Scope

- In scope: `docs/GUIA_PROYECTO_CLASIFICACION.md` (overview table rows 3, 6, 8,
  10; R2 in Step 1.2; Step 3 questions + D3.1 and D3.2; Step 6 D6.2 and D6.3;
  Step 8 questions + D8.1; Step 10 D10.3; common pitfalls 1, 2, 4; glossary
  entries) and this spec.
- Out of scope: any change to `src/`, `app/`, `docs/PREPROCESSING.md`,
  `docs/MODELING.md` or `docs/APP.md`, and the sections of the living guide
  owned by other teammates (#13, #15, #19, #21, #22, #23, #26–#31).

## Design

| File | Change |
|---|---|
| `specs/docs-living-guide-levi-contributions.md` | New. Branch spec. |
| `docs/GUIA_PROYECTO_CLASIFICACION.md` | Add D3.1 (#12), D3.2 (#14), D6.2 (#20), D6.3 (#24), D8.1 (#25), update D10.3 (#32), overview table, R2, common pitfalls and glossary. |

## Acceptance criteria

- [x] Step 3 documents #12 (D3.1) and #14 (D3.2) and answers the three guide questions
- [x] Step 6 documents #20 (D6.2) and #24 (D6.3) below D6.1 (#17)
- [x] Step 8 documents #25 (D8.1) and answers the four guide questions
- [x] Step 10 updates D10.3 with the completed #32 pipeline export and marks it `✅`
- [x] Overview table, R2, common pitfalls and glossary reflect the new entries
- [x] All numbers match `docs/PREPROCESSING.md`, `docs/MODELING.md` and `docs/APP.md`

## Verification

Documentation only; verify with `git diff` that only the intended sections of
`docs/GUIA_PROYECTO_CLASIFICACION.md` changed and that all metric values match
the verified outputs of `src/data_cleaning.py`, `src/feature_scaling.py`,
`src/logistic_regression.py`, `src/neural_network.py`, `src/final_metrics.py`
and `src/export_model.py`.
