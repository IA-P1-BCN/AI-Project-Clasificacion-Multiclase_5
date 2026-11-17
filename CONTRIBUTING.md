# Contributing Guide

This document defines the Git workflow, branch model, spec-driven rules and
commit convention for the project. AI coding agents must also follow
[AGENTS.md](AGENTS.md).

## Branch model

We use a simplified **Git Flow**:

| Branch | Purpose |
|---|---|
| `main` | Stable, release-ready code. No direct commits (team rule); updated only by merging `develop` at milestone deliveries. |
| `develop` | Integration branch. Every feature, fix or docs branch merges here first via a Pull Request. |
| `feature/<issue>-<short-kebab-description>` | New work tied to a GitHub issue. Branches **off `develop`**, merges back into `develop`. |
| `fix/<issue>-<short-kebab-description>` | Bug fixes tied to an issue (or `fix/<short-kebab-description>` for follow-ups). |
| `docs/<short-kebab-description>` | Documentation-only updates without a dedicated feature ticket. |

Examples of branch names:

```text
feature/14-feature-scaling
feature/25-compute-final-metrics
feature/34-backend-api-fastapi
fix/dataset-selection-wording
docs/eda-retroactive-specs
```

### Typical flow

1. Sync `develop` and branch off `origin/develop`:

   ```bash
   git fetch origin
   git checkout -b feature/<issue>-<short-kebab-description> origin/develop
   ```

2. Write the branch specification in `specs/<branch-name-with-dashes>.md`
   (e.g. `specs/feature-14-feature-scaling.md`) **before** writing code (see [specs/README.md](specs/README.md) and the shared
   vocabulary in [specs/ontology.md](specs/ontology.md)).
3. Implement the change, run the module (`python src/<module>.py`), verify every
   acceptance criterion, and update the relevant file in `docs/` plus the spec
   checklist.
4. Stage and commit **by explicit file path** (never `git add -A` or `git add .`,
   so local IDE or environment files never slip in):

   ```bash
   git add specs/feature-<issue>-<slug>.md src/<module>.py docs/<DOC>.md
   git commit -m "feat(<scope>): <imperative subject> (#<issue>)"
   ```

5. Push the branch and open a **Pull Request** (`feature/<...>` → `develop`);
   at least one teammate reviews it and CI must pass before merging.

## Spec-driven workflow and repository hygiene

- **One issue, one branch, one spec.** Every branch adds or updates its spec in
  [specs/](specs/README.md) (`specs/<branch-name-with-dashes>.md`).
- **English only** for code, comments, docstrings, commit messages, specs, PRs
  and documentation.
- **No data or model artifacts in Git.** `data/raw/`, `data/processed/` and
  `models/` are git-ignored (except `.gitkeep` and [data/README.md](data/README.md)).
  Never commit dataset files (`covtype.data`, `*.csv`) or serialized models
  (`*.joblib`, `*.pkl`).
- **No data leakage.** Any step that learns parameters from data (scalers,
  clippers, encoders, feature selectors, estimators) is fitted on training rows
  only, ideally inside a scikit-learn `Pipeline`.

## Commit convention — Conventional Commits

Format:

```text
<type>(<optional scope>): <short description in imperative mood>
```

**Types**

| Type | Use for |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `chore` | Tooling, config, scaffolding, dependencies |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or fixing tests |
| `style` | Formatting, no code-meaning change |
| `ci` | CI/CD configuration |

**Examples**

```text
feat(preprocessing): scale numeric features without data leakage (#14)
feat(modeling): train logistic regression under the CV protocol (#20)
feat(api): add FastAPI backend with /predict (#34)
docs(deliverables): complete DELIVERABLES.md and APP.md (#45)
chore(reproducibility): pin pydantic and document run steps (#46)
```

Keep the subject line under ~72 characters, write it in the imperative mood
("add", not "added"/"adds"), and reference the issue number (`(#<n>)`) in the PR
title or commit subject.

## Pull requests, squash/merge and branch cleanup

- **Squash or clean merge into `develop`.** When a feature branch has multiple
  work-in-progress or review-fixup commits, prefer **Squash and merge** on
  GitHub (with a Conventional Commit title referencing `(#<issue>)`) so
  `develop` keeps one readable commit per ticket.
- **Prune merged branches locally.** After a PR is merged into `develop`,
  clean up stale local branches and remote-tracking references:

  ```bash
  git checkout develop
  git pull --ff-only origin develop
  git fetch --prune origin
  git branch -d feature/<issue>-<short-kebab-description>
  ```

- **Milestone releases (`develop` → `main`).** Once a milestone's acceptance
  criteria and CI checks are green on `develop`, open a release Pull Request
  from `develop` into `main`.

## Continuous integration

Every pull request into `develop` or `main`, and every push to those branches,
runs [.github/workflows/ci.yml](.github/workflows/ci.yml) (#41):

- **Install, imports and tests:** installs [requirements.txt](requirements.txt)
  on the Python version of [.python-version](.python-version), imports every
  module of `src/` and `app/`, and runs `pytest` once a `tests/` folder exists.
- **Docker build:** builds the image without pushing it.

The result appears as checks at the bottom of the pull request. Run the import
check locally with `python scripts/check_imports.py`.

## Governance audit checks

Run these checks from the repository root to verify untracked artifacts,
documentation links and branch hygiene:

```bash
# 1. Verify no dataset or model artifacts are tracked in Git
python -c "import subprocess; tracked = [p for p in subprocess.check_output(['git', 'ls-files', 'data/', 'models/', '*.joblib', '*.pkl'], text=True).splitlines() if not p.endswith('.gitkeep') and p != 'data/README.md']; assert not tracked, tracked; print('ok    zero dataset/model artifacts tracked')"

# 2. Verify all relative links in CONTRIBUTING.md resolve
python -c "import pathlib, re; f = pathlib.Path('CONTRIBUTING.md'); missing = [t for t in re.findall(r'\]\((?!https?://|#)([^)]+)\)', f.read_text(encoding='utf-8')) if not (f.parent / t.split('#')[0]).resolve().exists()]; assert not missing, missing; print('ok    all CONTRIBUTING.md links resolve')"

# 3. Inspect active local branches and recent commit history
git branch -v
git log --oneline -n 20 origin/develop
```
