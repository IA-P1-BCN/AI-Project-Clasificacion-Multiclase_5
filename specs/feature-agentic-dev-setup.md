# Spec: feature/agentic-dev-setup

| | |
|---|---|
| Issue | none (tooling) |
| Milestone | M0 |
| Branch | `feature/agentic-dev-setup` (from `develop`) |
| Owner | @levifvy |
| Depends on | none |

## Goal

Give AI coding agents the same rules the team follows, so that agent-assisted
work respects Git Flow, the English-only rule and the no-leakage rule.

## Scope

- In scope: `AGENTS.md`, `specs/` (ontology, README with template, this spec),
  subagents in `.claude/agents/`, skills in `.claude/skills/`.
- Out of scope: any change to `src/`, `app/`, `docs/` or CI.

## Design

| File | Purpose |
|---|---|
| `AGENTS.md` | Tool-agnostic entry point: hard rules, conventions, workflow |
| `specs/ontology.md` | Shared vocabulary (domain, data, ML and process terms) |
| `specs/README.md` | Spec naming rule and template |
| `.claude/agents/preprocessing-engineer.md` | Implements M3 preprocessing issues |
| `.claude/agents/leakage-reviewer.md` | Read-only leakage and reproducibility review |
| `.claude/agents/docs-writer.md` | Updates docs and specs from verified results |
| `.claude/skills/start-issue-branch/SKILL.md` | Issue -> branch + spec |
| `.claude/skills/write-branch-spec/SKILL.md` | Writes the spec of the current branch |
| `.claude/skills/leakage-check/SKILL.md` | Leakage checklist |

## Acceptance criteria

- [x] `AGENTS.md` exists at the repository root and states the Git Flow, English-only and no-leakage rules
- [x] `specs/ontology.md` defines the dataset entities and column groups used by the code
- [x] Every branch created from now on has a spec in `specs/`
- [x] Subagents and skills have valid frontmatter (`name`, `description`)

## Verification

Documentation only; no code to run. Check that the column counts and class
shares in `specs/ontology.md` match `docs/EDA.md`.
