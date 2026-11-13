# Spec: feature/11-document-eda-findings

| | |
|---|---|
| Issue | #11 - [M2] Document EDA findings (docs/EDA.md) |
| Milestone | M2 |
| Branch | `feature/11-document-eda-findings` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | #7, #8, #9 (audit, class distribution, class EDA) |

> Written retroactively (ticket #11 was merged in PR #61 before the spec-driven
> workflow of PR #63 existed). It records what was built and verified.

## Goal

Consolidate the results and conclusions of the EDA into `docs/EDA.md`, so the
findings can be used for the M3 decisions.

## Scope

- In scope: a *Findings* section with a key findings table, recommendations for
  M3, the limitations of the EDA and a reproducibility table of the scripts.
- Out of scope: applying any recommendation (M3 tickets) and repeating the
  analysis.

## Design

| File | Change |
|---|---|
| `docs/EDA.md` | New *Findings* section (key findings, recommendations for M3 marked as to be confirmed by the team, limitations, reproducibility). |

Decision: every recommendation is an input for M3, not a decision. The
limitations are explicit: the 44 binary indicators were not analyzed against the
class, eta squared only sees differences between means, and the EDA uses the
whole dataset (the split of #16 came later).

## Acceptance criteria

- [x] `docs/EDA.md` is complete and readable
- [x] The findings are usable for M3 decisions

## Verification

Open `docs/EDA.md` and check that the *Findings* section lists the six key
findings, the five recommendations for M3, the limitations and the table of
scripts with the figures each one produces.
