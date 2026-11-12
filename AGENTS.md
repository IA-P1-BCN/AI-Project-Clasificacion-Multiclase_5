# AGENTS.md

Instructions for AI coding agents (Claude Code, Antigravity, Codex, Cursor, ...)
working in this repository. Humans should read [CONTRIBUTING.md](CONTRIBUTING.md)
first; this file adds what an agent needs on top of it.

## Project

Multiclass classification of forest cover type (UCI Covertype, 581,012 rows,
54 features, 7 classes). Team of four, work tracked as GitHub issues grouped in
milestones M0-M8. Shared vocabulary lives in [specs/ontology.md](specs/ontology.md);
use those terms and names exactly.

## Hard rules

1. **English only** for code, comments, docstrings, commit messages, specs and docs.
2. **Git Flow.** Never commit to `main` or `develop`. Branch off `develop`, open a
   Pull Request back into `develop`.
3. **One issue, one branch, one spec.** Every branch has a spec in `specs/`
   written before the code (see [specs/README.md](specs/README.md)).
4. **No data leakage.** Anything that learns from data (scalers, encoders,
   resamplers, feature selectors) is fitted on training data only, ideally
   inside a scikit-learn `Pipeline`.
5. **Raw data is immutable and untracked.** Never edit or commit files under
   `data/raw/`. Never commit model artifacts (`*.joblib`, `*.pkl`).
6. **Stay in scope.** Implement the issue you were given. If the work touches
   another teammate's issue, stop at the boundary and note it in the spec.
7. **Do not push, open PRs or close issues unless the human asks.**

## Branches and commits

- Branch name: `feature/<issue-number>-<short-kebab-description>`
  (e.g. `feature/14-feature-scaling`). Use `fix/<...>` for bug fixes. Work
  without an issue omits the number (e.g. `feature/agentic-dev-setup`).
- Commits follow Conventional Commits: `<type>(<scope>): <imperative subject>`,
  subject under ~72 characters. Reference the issue in the PR title, e.g.
  `feat(preprocessing): scale numeric features (#14)`.
- Stage files by explicit path. Do not use `git add -A` / `git add .`; the
  working tree may contain local IDE or environment changes.

## Repository layout

| Path | Content |
|---|---|
| `src/` | Library code and runnable scripts (flat modules, run as `python src/<module>.py`) |
| `app/` | Streamlit application |
| `data/raw/`, `data/processed/` | Datasets (git-ignored) |
| `models/` | Trained artifacts (git-ignored) |
| `docs/` | Project documentation (`EDA.md`, `MODELING.md`, ...) and figures |
| `specs/` | Ontology and one spec per branch |
| `.claude/agents/`, `.claude/skills/` | Subagents and skills for agentic development |

## Code conventions

- Python 3.11, dependencies pinned in `requirements.txt`. Do not add a
  dependency without saying so in the spec and the PR description.
- Reuse existing helpers instead of redefining them: `load_raw` and `COLUMNS`
  in `src/data_audit.py` are the single source for loading the dataset and for
  column names.
- Each module starts with a one-line docstring naming its issue, exposes pure
  functions, and has a `main()` guarded by `if __name__ == "__main__":` that
  prints a reproducible summary.
- Use `random_state=42` wherever randomness is involved.
- Document results in `docs/` with the command that reproduces them.

## Setup and commands

```bash
docker compose up                  # run the app at http://localhost:8501
python -m venv .venv               # local alternative
pip install -r requirements.txt
python src/data_audit.py           # checks that data/raw/covtype.data is in place
```

The dataset is not in the repository; see the *Dataset* section of the README.

## Workflow for a new task

1. Read the issue (`gh issue view <n>`) and `specs/ontology.md`.
2. Create the branch from an up-to-date `develop` (skill `start-issue-branch`).
3. Write `specs/<branch-name-with-dashes>.md` from the template.
4. Implement, run the module, and verify every acceptance criterion.
5. Update the relevant file in `docs/` and tick the spec checklist.
6. Commit by explicit path. Report what was verified and what was not.

## Subagents and skills

| Kind | Name | Use it for |
|---|---|---|
| Subagent | `preprocessing-engineer` | Implementing M3 cleaning / preprocessing issues |
| Subagent | `leakage-reviewer` | Read-only review of a diff for data leakage and reproducibility |
| Subagent | `docs-writer` | Updating `docs/` and specs from verified results |
| Skill | `start-issue-branch` | Creating the Git Flow branch and its spec from an issue |
| Skill | `write-branch-spec` | Writing or updating the spec of the current branch |
| Skill | `leakage-check` | Checklist to verify a preprocessing change does not leak |
