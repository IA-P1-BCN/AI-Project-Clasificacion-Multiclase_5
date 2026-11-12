# Specs

Spec-driven development: every branch has a spec written **before** the code.

- [`ontology.md`](ontology.md): shared vocabulary. Read it first.
- One file per branch, named after the branch with `/` replaced by `-`
  (branch `feature/14-feature-scaling` -> `specs/feature-14-feature-scaling.md`).
- The spec is committed in its own branch and merged with it.

## Template

```markdown
# Spec: <branch name>

| | |
|---|---|
| Issue | #<n> - <title> |
| Milestone | M# |
| Branch | `feature/<n>-<description>` (from `develop`) |
| Owner | @<github-user> |
| Depends on | #<n> / none |

## Goal

One or two sentences: what changes and why.

## Scope

- In scope: ...
- Out of scope: ... (name the issue that owns it)

## Design

Files to add or change, public functions, decisions and their reasons.

## Acceptance criteria

- [ ] Criteria copied from the issue, plus any added here.

## Verification

Commands to run and the expected result.
```
