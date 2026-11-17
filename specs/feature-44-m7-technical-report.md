# Spec: feature/44-m7-technical-report

| | |
|---|---|
| Issue | #44 - [M7] Technical report (metrics and analysis) |
| Milestone | M7 |
| Branch | `feature/44-m7-technical-report` (from `develop`) |
| Owner | @carovasq |
| Depends on | M5 evaluation (#25, #26, #27, #30) and modeling (#19–#24, #29), all merged into `develop` |

## Goal

Deliver a single, self-contained technical report that consolidates the
project's metrics and analysis — methodology, model comparison, final metrics,
confusion matrix, feature importance and error analysis — so a reader gets the
whole story and the key decisions from one document, with pointers to the
detailed per-stage docs.

## Scope

- In scope:
  - New `docs/TECHNICAL_REPORT.md`: problem and data, methodology, preprocessing
    decisions, model comparison and selection, final metrics on
    validation/test, per-class metrics, confusion matrix, feature importance
    (MDI + permutation + SHAP), error analysis, limitations and conclusions,
    and how to reproduce and export the report.
  - Links from `README.md` and `docs/DELIVERABLES.md`, and ticking the
    "Technical report" deliverable in `DELIVERABLES.md`.
  - Every number traced to the code that produces it and to the detailed doc
    (`EDA.md`, `PREPROCESSING.md`, `MODELING.md`) and figures it already lives
    in — no new computation, no invented values.
- Out of scope:
  - Re-running the pipeline or changing any `src/` behavior or results.
  - New analysis beyond what #25–#30 already produced.
  - The business and code presentations (M8, #48/#49) and the final README
    rewrite (#43).
  - Committing a binary export (PDF/DOCX); the report is Markdown and the
    export command is documented.

## Design

| File | Change |
|---|---|
| `docs/TECHNICAL_REPORT.md` | New consolidated report. |
| `README.md` | One line + repository-tree entry pointing to it. |
| `docs/DELIVERABLES.md` | Tick the technical-report deliverable and link the report. |

Decisions and reasons:

- **A consolidated report, not a copy of the detailed docs.** `EDA.md`,
  `PREPROCESSING.md` and `MODELING.md` are the per-stage records; this report is
  the executive, end-to-end read that stitches their verified results together
  and states the decisions. It cites them instead of duplicating every table.
- **Markdown in `docs/`, consistent with the repo.** Every other deliverable is
  English Markdown under `docs/`, reviewed via PR. "Export as document" is met by
  a documented `pandoc` command (to PDF/DOCX) rather than committing a binary,
  which the repo keeps out of Git.
- **Numbers come only from merged, reproduced results.** The report reuses the
  figures in `docs/figures/` and the tables already verified in the detailed
  docs; each section names the script that reproduces it. The headline result is
  the exported untuned Random Forest: validation accuracy 0.9520 / macro F1
  0.9186, test 0.9510 / 0.9199, overfitting gap +4.80 pp.
- **Honest status notes.** Where the shipped model differs from the best
  measured configuration (tuning #29 and feature engineering #18 are not yet in
  the exported pipeline), the report says so rather than quoting the optimistic
  CV numbers as the delivered result.

## Acceptance criteria

Copied from issue #44:

- [x] Compile metrics, confusion matrix, feature importance, error analysis
- [x] Explain methodology and decisions
- [x] Export as document
- [x] Technical report delivered

## Verification

1. Every relative link and figure path in `docs/TECHNICAL_REPORT.md` resolves to
   an existing file.
2. Every metric in the report matches the corresponding table in `EDA.md`,
   `PREPROCESSING.md` or `MODELING.md` (which are the reproduced results).
3. The documented `pandoc` export command produces a document from the Markdown.

Result (2026-11-17):

- All 4 figure paths (`class_distribution`, `feature_importance`,
  `shap_summary_bar`, `error_analysis`) and all 6 cross-document links
  (`EDA`, `PREPROCESSING`, `MODELING`, `APP`, `REPRODUCIBILITY`, `DELIVERABLES`)
  resolve to existing files.
- Spot-checked numbers against the source docs: headline validation/test
  metrics (0.9520/0.9186, 0.9510/0.9199), overfitting gap +4.80 pp, the model
  comparison ranking, per-class/test tables, test confusion matrix, the three
  importance rankings and the error-analysis tables all match
  `MODELING.md` / `EDA.md` / `PREPROCESSING.md`.
- `pandoc` is a standard converter but is **not installed on this machine**, so
  the export command is documented but was not run here; it needs a local
  `pandoc` (and a LaTeX engine for PDF).
