# Spec: feature/3-select-definitive-dataset

| | |
|---|---|
| Issue | #3 - [M1] Select the definitive dataset (Dry Bean / Wine / Forest Cover Type) |
| Milestone | M1 |
| Branch | `feature/3-select-definitive-dataset` (from `develop`) |
| Owner | @carovasq |
| Depends on | #2 (M1 problem definition, merged in PR #57) |

## Goal

The project already runs on Covertype de facto, but the *justified comparison*
of the three suggested candidates that issue #3 asks for does not exist in the
repository. This branch records that decision in writing so the choice is
documented and testable.

## Scope

- In scope: a dataset-selection decision record comparing Wine, Dry Bean and
  Forest Cover Type on size, classes, balance, feature types and availability,
  and naming the chosen dataset with justification; links to it from `README.md`
  and `SPEC.md` section 3.
- Out of scope:
  - Dataset **source, version, size and checksum** — owned by issue #4
    (`data/README.md`); the "Source & version" line in `SPEC.md` section 3 is
    left untouched.
  - Downloading the data and the audit of its real shape — issue #4 / M2.

## Design

| File | Change |
|---|---|
| `docs/DATASET_SELECTION.md` | New. Candidate comparison table + decision + justification. The real deliverable. |
| `SPEC.md` | Section 3: add a one-line selection rationale linking to the decision record. Do not touch the "Source & version" line (issue #4). |
| `README.md` | *Dataset* section: link to the decision record. |

Decisions:

- The selection rationale lives in `docs/`, not inside `SPEC.md`, to keep the
  full comparison out of the contested section 3 and avoid overlap with issues
  #2 and #4.
- Candidate facts are cited from each dataset's UCI page; Covertype's shape and
  class shares are already recorded in `specs/ontology.md` and verifiable with
  `python src/data_audit.py`.

## Acceptance criteria

Copied from issue #3:

- [ ] Evaluate candidates: Dry Bean, Wine, Forest Cover Type
- [ ] Compare size, number of classes, feature types and availability
- [ ] Choose one dataset and document the justification
- [ ] Record the decision in SPEC.md / README
- [ ] One definitive dataset selected with written justification
- [ ] Dataset has >= 3 classes and is suitable for classification (Covertype: 7)
- [ ] Decision documented

## Verification

Documentation-only change; verified by reading, not by running code.

- `docs/DATASET_SELECTION.md` names one dataset (Covertype) and justifies it
  against both alternatives on all five axes.
- `README.md` and `SPEC.md` section 3 link to the decision record.
- `git diff --name-only origin/develop` lists only the three files above.
