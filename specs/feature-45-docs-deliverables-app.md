# Spec: feature/45-docs-deliverables-app

| | |
|---|---|
| Issue | #45 - [M7] Docs (DELIVERABLES.md, APP.md) |
| Milestone | M7 |
| Branch | `feature/45-docs-deliverables-app` (from `develop`) |
| Owner | @levifvy |
| Depends on | #32 (model export, merged), #34 (FastAPI backend, merged), #36 (retraining pipeline, merged), #37 (database integration, merged), #25 (final metrics, merged) |

## Goal

Complete `docs/DELIVERABLES.md` with the verified status and evidence of every
required deliverable, technical requirement and delivery level, and complete
`docs/APP.md` with the application requirements, architecture, Dockerization,
deployment and usage instructions, verifying that all links resolve.

## Scope

- In scope:
  - `docs/DELIVERABLES.md`: update the `Required deliverables` and `Technical
    requirements` checklists with concrete repository evidence, and replace the
    `_To be filled in M7/M8._` placeholder in `Final checklist` with a
    delivery-level verification table (`Esencial`, `Medio`, `Avanzado`,
    `Experto`) and the project board links.
  - `docs/APP.md`: align `Functional requirements` and `Architecture` with the
    implemented modules (`app/main.py`, `app/api.py`, `app/serving.py`,
    `app/schemas.py`, `src/export_model.py`, `src/database.py`,
    `src/retraining.py`), and replace the stub `Dockerization`, `Deployment`
    and `Usage` sections (`_To be filled in M6._`) with full, reproducible
    instructions for local and Docker execution.
- Out of scope:
  - Completing `README.md` (#43, @nagicome03).
  - Standalone technical report narrative (#44, @carovasq).
  - Final `requirements.txt` pinning and reproducibility guide (#46).
  - Detailed Docker/compose troubleshooting guide (#47, @Leandroletoile,
    @carovasq).
  - Implementing the interactive Streamlit prediction UI (#33, @nagicome03),
    the production feedback endpoint/dashboard (#35, @carovasq), multi-service
    container orchestration (#38, @carovasq), or live cloud deployment (#39).

## Design

| File | Change |
|---|---|
| `docs/DELIVERABLES.md` | Tick verified deliverables and technical requirements, link every item to its module or documentation file, and fill the *Final checklist* by delivery level (`Esencial`, `Medio`, `Avanzado`, `Experto`). |
| `docs/APP.md` | Expand *Functional requirements* and *Architecture*, and complete *Dockerization*, *Deployment* and *Usage* with concrete commands and environment variables. |

Decisions and reasons:

- **Honest status reporting in `docs/DELIVERABLES.md`.** Items already merged
  into `develop` are ticked (`[x]`) with links to the exact files and commands
  that verify them (`src/final_metrics.py` for the `+4.80` pp `< 5%`
  `overfitting_gap`, `app/api.py` and `src/export_model.py` for inference,
  `Dockerfile` and `docker-compose.yml` for Dockerization, `docs/` for
  documentation). Items whose tickets are still open (#33 Streamlit UI, #40
  unit tests, #48 business presentation, #49 technical code presentation) are
  explicitly marked with their owning issue numbers rather than ticked
  prematurely.
- **Complete `docs/APP.md` without stepping into #33, #35, #38, #39 or #47.**
  `docs/APP.md` already documents the FastAPI backend (#34), model export (#32),
  MySQL/SQLite persistence (#37) and retraining pipeline (#36). This branch
  completes the remaining sections (*Functional requirements*, *Architecture*,
  *Dockerization*, *Deployment*, *Usage*) so a reader can export the model, run
  the backend and frontend locally or via Docker Compose, and query `/health`
  and `/predict`, while clearly noting the boundaries with #33, #35, #38, #39
  and #47.
- **Link verification.** Every relative link in `docs/DELIVERABLES.md` and
  `docs/APP.md` is checked programmatically from the `docs/` directory so no
  broken path is introduced.

## Acceptance criteria

- [x] Update DELIVERABLES.md checklist
- [x] Document app requirements and usage in APP.md
- [x] Verify links
- [x] DELIVERABLES.md and APP.md complete
- [x] No `_To be filled in M6._` or `_To be filled in M7/M8._` placeholders remain in `docs/DELIVERABLES.md` or `docs/APP.md` (added)

## Verification

```bash
python -c "import pathlib, re; root = pathlib.Path('.'); [print(f, '->', t, 'EXISTS' if (f.parent / t.split('#')[0]).resolve().exists() else 'MISSING') for f in [pathlib.Path('docs/DELIVERABLES.md'), pathlib.Path('docs/APP.md')] for t in re.findall(r'\]\((?!https?://|#)([^)]+)\)', f.read_text(encoding='utf-8'))]"
```

Expected: every relative link in `docs/DELIVERABLES.md` and `docs/APP.md`
prints `EXISTS`, and neither file contains `_To be filled`.

Observed (2026-11-17):

- All relative links across `docs/DELIVERABLES.md` and `docs/APP.md` resolved
  and printed `EXISTS` (0 `MISSING`). A second check that also resolves the
  `#anchor` fragments against the target headings found 0 broken anchors.
- Neither `docs/DELIVERABLES.md` nor `docs/APP.md` contains `_To be filled`.
- `git status --short` shows only `specs/feature-45-docs-deliverables-app.md`,
  `docs/DELIVERABLES.md` and `docs/APP.md`.

Review fixes (2026-11-17, after rebasing onto `develop` with #26 and #29
merged):

- `docs/DELIVERABLES.md`: hyperparameter optimization marked done with the #29
  results (Random Forest `0.9123 → 0.9326`, XGBoost `0.8489 → 0.9240`, 5-fold
  macro F1), noting that the exported pipeline of #32 still uses the default
  Random Forest; feature importance marked done (#26) with error analysis still
  pending (#27); issue count corrected to 54; board link points to the Team 5
  project (`/orgs/IA-P1-BCN/projects/61`) instead of the organization list.
- `docs/APP.md`: `docker-compose.yml` only publishes port `8501`, so the
  documented `docker compose exec app uvicorn ...` was unreachable from the
  host (`curl http://localhost:8000/health` failed with exit 7). Replaced with
  `docker compose run --rm -p 8000:8000 app uvicorn app.api:app --host 0.0.0.0 --port 8000`;
  verified in Docker that `GET /health` returns `model_loaded: true`,
  `db_connected: true` and that the documented `POST /predict` payload returns
  `cover_type` 2 (Lodgepole Pine, `confidence` 0.95) from the host. Clarified
  that `.env.example` lists only the database variables (`MODEL_PATH` is
  optional).

Second review round (2026-11-17, PR #97, after merging `develop` with #27 via
#96 and #46 via #98):

- `docs/APP.md` conflict in *Usage*: kept the full quick-start section of this
  branch and added a pointer to [REPRODUCIBILITY.md](../docs/REPRODUCIBILITY.md)
  (#46) as the reference for the pinned environment, run steps and clean-clone
  checklist, so there is a single source of truth.
- `docs/APP.md`: MySQL port shown as `${MYSQL_PORT:-3306}:3306` (#98) and
  `MYSQL_PORT` added to both environment-variable tables; local run now states
  Python 3.11 (`python3.11 -m venv .venv`), since the pinned versions do not
  install on 3.13.
- `docs/DELIVERABLES.md`: error analysis marked done (#27:
  `src/error_analysis.py`, `docs/figures/error_analysis.png`) and removed from
  the remaining items; tuned CV scores of #29 flagged as slightly optimistic
  (parameters selected on the same `train` folds; unbiased measure in #28 and
  #25); *Technical report* (#44 open) and *Documentation* (#43 open) moved back
  to in progress instead of `[x]`.
