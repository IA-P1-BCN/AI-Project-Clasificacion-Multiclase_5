# Spec: feature/43-final-readme

| | |
|---|---|
| Issue | #43 - Final README |
| Milestone | M7 |
| Branch | `feature/43-final-readme` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | the work the README describes; all of it is merged except the move of Render to `main` (#39 follow-up) and the presentations (#48, #49) |

## Goal

Replace the starting README with the final one: what the project does, its results,
how to run it, how it is built, what it does not do, and where each document is.

## Scope

- In scope: `README.md` and this spec.
- Out of scope:
  - Any change to code, tests or behaviour.
  - The other documents. Some still describe the Streamlit app as the M0
    placeholder (`docs/REPRODUCIBILITY.md`, `docs/DOCKER.md`); that is fixed in its own change.
  - The presentation (#48, #49).

## Design

- **Order:** summary and live demo, results, how it works (diagram), delivery levels,
  quick start, API, methodology, limitations, documentation map, structure, team,
  contributing, data source. The reader can run the project from the quick start
  without opening another file.
- **Diagram:** a Mermaid flowchart, which GitHub renders, so there is no image to keep in sync.
- **Evidence:** every number comes from a document of the repository
  (`docs/TECHNICAL_REPORT.md`, `docs/MODELING.md`, `docs/APP.md`, `docs/AB_TESTING.md`,
  `docs/DRIFT_MONITORING.md`). Nothing is recomputed here.
- **Honest status:** a limitations section states what is not in the shipped model
  (tuned forest, engineered features), why the cloud serves another model, and
  the scope of the A/B rule and of drift monitoring.
- **Kept from the old README:** the delivery levels, the dataset steps and the
  contributing section, shortened and linked to the documents that hold the detail.

## Acceptance criteria

- [ ] The README states the problem, the dataset and the live demo URL.
- [ ] It reports the validation and test metrics and the overfitting gap.
- [ ] It has an architecture diagram that GitHub renders.
- [ ] A clean clone can be run following only the quick start.
- [ ] It lists the API endpoints with a working example.
- [ ] It states the limitations.
- [ ] It links every document of `docs/`, `SPEC.md` and `specs/`.
- [ ] It names the team and the data source.

## Verification

- Every relative link of `README.md` resolves against `develop` (checked with a script).
- Each number was compared with the document it comes from.
- The quick start commands match `docs/REPRODUCIBILITY.md` and `docs/DOCKER.md`.
- The Mermaid block renders in the pull request preview.