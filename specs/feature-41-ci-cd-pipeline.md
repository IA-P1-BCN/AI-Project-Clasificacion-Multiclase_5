# Spec: feature/41-ci-cd-pipeline

| | |
|---|---|
| Issue | #41 - [M6] CI/CD pipeline (GitHub Actions) |
| Milestone | M6 |
| Branch | `feature/41-ci-cd-pipeline` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | #40 (unit tests, not started: the workflow runs them as soon as a `tests/` folder exists), #34 (API, PR #81: its modules are checked once merged) |

## Goal

Automate checks with GitHub Actions so that a pull request that breaks the
installation, an import or the Docker build is flagged before it reaches
`develop`.

## Scope

- In scope: a workflow that runs on pull requests and pushes to `develop` and
  `main`; installing the pinned requirements; an import check of every module;
  running `pytest` when tests exist; a Docker build step; a short description
  in `CONTRIBUTING.md`.
- Out of scope:
  - Writing the tests (#40).
  - Auto-deploy, optional in the issue: it depends on the cloud deployment
    (#39).
  - Changes to the `Dockerfile` or `docker-compose.yml` (#38).
  - Making the checks mandatory to merge: that is a branch protection setting
    of the repository, done by an administrator, not a file in the code.

## Design

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | New. Two jobs: *Install, imports and tests* and *Docker build*. |
| `scripts/check_imports.py` | New. Imports every module of `src/` and `app/`, exits 1 if any fails. |
| `CONTRIBUTING.md` | New section *Continuous integration*. |

Decisions:

- **Triggers.** Pull requests into `develop` / `main`, and pushes to those two
  branches. A feature branch is covered by its pull request, so it does not run
  twice. A new push cancels the run still in progress for the same branch.
- **Same environment as the Docker image.** Python from `.python-version`
  (3.11) and the pinned `requirements.txt`. Local machines run newer versions
  than the pins (for example scikit-learn 1.9.1 and XGBoost 3.4.1 against 1.5.1
  and 2.1.1), so this is where code that only works with newer versions shows up.
- **Import check instead of tests, for now.** There are no tests yet. Importing
  every module of `src/` and `app/` catches missing dependencies, syntax errors
  and broken imports, and covers the API (#34) as soon as it is merged. It does
  not train models or run pipelines: that needs the dataset, which is not in the
  repository, and would be slow. `app/main.py` is a Streamlit script that runs
  its UI on import, so it is skipped.
- **Tests do not block this ticket.** The step runs `pytest` only when
  `tests/**/test_*.py` exists. #40 must add `pytest` (and `httpx` for the API
  tests) to `requirements.txt`.
- **Docker.** Built with Buildx and the GitHub cache, without pushing.
- **Safety.** Read-only token, 20 minute timeout per job.
- Actions are pinned to major versions (`checkout` v4, `setup-python` v5,
  `setup-buildx-action` v3, `build-push-action` v6).
- No new dependency in `requirements.txt`.

## Acceptance criteria

- [ ] CI runs automatically (only if time allows)
- [ ] Add workflow to run tests on push
- [ ] Add Docker build step
- [ ] A change that breaks an import or the Docker build makes the check fail

## Verification

1. Open the pull request. In the *Checks* of the pull request, the workflow
   *CI* shows two jobs, *Install, imports and tests* and *Docker build*, both
   green; the *Run tests* step is skipped because there is no `tests/` folder.
2. `python scripts/check_imports.py` prints `ok` for every module and exits 0;
   if a module imports something that does not exist, it prints `FAIL` with the
   error and exits 1.
3. On a throwaway branch that is not merged, add `import nonexistent_module` to
   a file in `src/` and open a pull request: the *Install, imports and tests*
   job fails.