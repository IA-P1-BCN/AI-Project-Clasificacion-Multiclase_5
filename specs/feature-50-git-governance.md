# Spec: feature/50-git-governance

| | |
|---|---|
| Issue | #50 - [M8] Git governance (branches, clean commits) |
| Milestone | M8 |
| Branch | `feature/50-git-governance` (from `develop`) |
| Owner | @levifvy |
| Depends on | Continuous across M0–M8; #41 (CI workflow in `CONTRIBUTING.md`, merged) |

## Goal

Audit the repository's branch structure (`main`, `develop`, `feature/*`,
`fix/*`, `docs/*`), commit history and untracked-artifact rules, clean up local
feature branches already merged or squash-merged into `develop`, and complete
`CONTRIBUTING.md` so the team's Git Flow, spec-driven workflow, staging rules
and branch-cleanup procedures are documented in one place.

## Scope

- In scope:
  - `CONTRIBUTING.md`: align branch naming with `AGENTS.md`
    (`feature/<issue-number>-<short-kebab-description>`), document the
    spec-first requirement (`specs/<branch-with-dashes>.md` and
    `specs/ontology.md`), explicit-path staging (`git add <path>`, never
    `git add -A` / `git add .`), artifact exclusion (`data/raw/`,
    `data/processed/`, `models/`), PR squash/merge and post-merge branch cleanup
    (`git fetch --prune`, `git branch -d`), and reproducible governance audit
    commands.
  - Local branch hygiene: delete the 12 local branches whose pull requests
    (#63, #64, #65, #66, #67, #73, #74, #85, #87, #88, #89, #90) are already
    merged or squash-merged into `origin/develop`.
- Out of scope:
  - Rewriting published history on `origin/develop` or `origin/main`
    (protected/shared integration branches must never be force-pushed).
  - Deleting remote branches on `origin` or closing GitHub issues without
    explicit user instruction (`AGENTS.md` hard rule #7).
  - Final M8 release merge from `develop` into `main` (#51).

## Design

| File | Change |
|---|---|
| `CONTRIBUTING.md` | Expand *Branch model* (`feature/<issue>-<slug>`, `fix/<issue>-<slug>`, `docs/<slug>`), add *Spec-driven workflow and repository hygiene*, add *Pull requests, squash/merge and branch cleanup*, and add *Governance audit checks*. |
| `AGENTS.md` | Add the `docs/<short-kebab-description>` branch prefix so it matches `CONTRIBUTING.md`. |
| `specs/feature-50-git-governance.md` | Record the M0–M8 branch, commit, spec-coverage and untracked-artifact audit results. |

Decisions and reasons:

- **Do not rewrite `origin/develop` or `origin/main`.** The "squash/clean
  commit history" task is interpreted as *keep history clean going forward*,
  not as squashing published history. All pull requests merged into `develop`
  since #54 follow Conventional Commits (`feat`, `fix`, `docs`, `chore`, `ci`,
  `style`, `refactor`) and carry their branch specs under `specs/`. Squashing
  or rebasing shared history on `develop` would require a force-push and
  invalidate open teammate branches (PRs #97, #99, #100 at the time of
  writing). Instead, we clean local already-merged branches and document the
  squash-merge / cleanup workflow in `CONTRIBUTING.md` so future merges stay
  readable.
- **Known non-conventional commits are left as they are.** The pre-M0 commits
  (`e391018`, `885b567`, `84466c8`, `926c9c5`, `504c35c`) and one early M0
  commit (`bfd83da refactor spec and readme`, 2026-11-12) do not follow
  Conventional Commits. They are part of published history and are not
  rewritten, for the reason above.
- **`docs/<slug>` prefix added to `AGENTS.md` too.** The team already used
  `docs/*` branches for documentation-only work without an issue
  (`docs/ci-spec-results`, `docs/eda-retroactive-specs`). The prefix is
  documented in both `CONTRIBUTING.md` and `AGENTS.md` so humans and agents
  follow the same naming rules.
- **Single source of truth for human and agent contributors.** `AGENTS.md`
  already requires `feature/<issue-number>-<short-kebab-description>`, one spec
  per branch in `specs/`, and explicit-path staging (`git add <path>`), whereas
  `CONTRIBUTING.md` still showed early M0 examples (`feature/m0-docker-infra`)
  and omitted the spec and explicit-staging rules. Aligning `CONTRIBUTING.md`
  ensures humans and agents follow the exact same rules.
- **Reproducible governance checks.** `CONTRIBUTING.md` lists one-liner
  checks anyone can run before the M8 release:
  1. Zero files under `data/raw/`, `data/processed/` or `models/` (other than
     `.gitkeep` and `data/README.md`) and zero `*.joblib` / `*.pkl` artifacts
     are tracked by Git.
  2. Every relative link in `CONTRIBUTING.md` resolves.
  3. `git branch -v` and `git log --oneline` for a manual review of branches
     and commit subjects. Spec coverage and Conventional Commits compliance
     were audited manually for this spec (see *Observed*); they are not
     automated.

## Acceptance criteria

- [x] Review branch structure (main/develop + feature branches)
- [x] Squash/clean commit history: published history is not rewritten (see
  *Decisions*); merged local branches were removed and the squash-merge and
  cleanup workflow is documented for future PRs
- [x] Document contribution flow
- [x] Repo history clean and branches well managed
- [x] Zero dataset or model binary artifacts (`data/raw/*`, `data/processed/*`,
  `models/*.joblib`, `*.pkl`) are tracked in Git (criterion added by this spec)

## Verification

```bash
python -c "import subprocess, pathlib, re; tracked = [p for p in subprocess.check_output(['git', 'ls-files', 'data/', 'models/', '*.joblib', '*.pkl'], text=True).splitlines() if not p.endswith('.gitkeep') and p != 'data/README.md']; assert not tracked, tracked; print('ok    zero dataset/model artifacts tracked'); f = pathlib.Path('CONTRIBUTING.md'); missing = [t for t in re.findall(r'\]\((?!https?://|#)([^)]+)\)', f.read_text(encoding='utf-8')) if not (f.parent / t.split('#')[0]).resolve().exists()]; assert not missing, missing; print('ok    all CONTRIBUTING.md links resolve')"
git branch -v
```

Expected: `ok    zero dataset/model artifacts tracked`, `ok    all
CONTRIBUTING.md links resolve`, and `git branch -v` lists none of the 12
previously merged local branches.

Observed (2026-11-17):

- Branch & commit audit across `origin/develop` (`2cdac68`): 40 pull requests
  (#54–#93) merged into `develop`, all post-M0 commits follow Conventional
  Commits (`feat`, `fix`, `docs`, `chore`, `ci`, `style`, `refactor`) except
  `bfd83da refactor spec and readme` (see *Decisions*), and all
  merged feature branches have their specs in `specs/` (`35 files in specs/`).
- Untracked-artifact check passed: `ok    zero dataset/model artifacts tracked`
  (only `.gitkeep` and `data/README.md` are tracked under `data/` and
  `models/`).
- Link check on `CONTRIBUTING.md` passed: `ok    all CONTRIBUTING.md links
  resolve`.
- Local branch cleanup: removed the 12 already-merged / squash-merged local
  branches (`docs/living-guide-levi-contributions`,
  `feature/4-document-dataset-source`, `feature/12-missing-values-duplicates`,
  `feature/14-feature-scaling`, `feature/20-train-logistic-regression`,
  `feature/24-neural-network-mlp`, `feature/25-compute-final-metrics`,
  `feature/32-export-model-pipeline`, `feature/36-retraining-pipeline`,
  `feature/37-database-integration`, `feature/agentic-dev-setup`,
  `feature/m0-dev-environment-config`), leaving only `develop` and the active
  M7/M8 branches (`feature/45-docs-deliverables-app`,
  `feature/46-reproducibility-requirements-run-steps`,
  `feature/50-git-governance`).
- The branch diff against `develop` touches only `AGENTS.md`,
  `CONTRIBUTING.md` and `specs/feature-50-git-governance.md`.
