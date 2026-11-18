# Spec: docs/user-stories

| | |
|---|---|
| Issue | none (documentation of the user stories of the project) |
| Milestone | M7 |
| Branch | `docs/user-stories` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | the issues the stories refer to (#1 to #53); all are merged except #39 (cloud deployment, in progress) and the presentations (#48, #49) |

## Goal

Write the user stories of the project, with acceptance criteria, so that what the
system does can be read as needs of the people who use, build, run and review it,
and so that each story can be traced to the issues that implement it.

## Scope

- In scope: `docs/USER_STORIES.md` (new), one line each in `README.md` and in the
  documentation list of `docs/DELIVERABLES.md`, and this spec.
- Out of scope:
  - Any change to the code, the tests or the behaviour of the system. Features that
    are missing are written down as not built (the feedback form of the app in
    US-05) or as not covered, not implemented here.
  - The living guide (`docs/GUIA_PROYECTO_CLASIFICACION.md`): it is also edited by
    other open branches, so its entry is added separately to avoid conflicts.
  - Changing the status labels of `docs/DELIVERABLES.md`; some of its rows are older
    than the merged work.

## Design

- **Users:** four, taken from who actually touches the system: forest analyst
  (uses the app), data scientist (builds and evaluates the model), ML engineer
  (runs and monitors it) and reviewer (reads and reproduces it).
- **Format:** "As a ..., I want ... so that ...", followed by Given / When / Then
  criteria, the delivery level of `docs/DELIVERABLES.md`, the issues and the status.
  The `Must` / `Should` / `Could` priority is not copied: it lives in the labels of
  each issue and would go out of date here.
- **Grouping:** A predicting forest cover, B building and evaluating the model,
  C running and monitoring the system, D reviewing and reproducing the project.
  23 stories, with a summary table at the top.
- **Evidence:** every number and every behaviour in a criterion comes from a
  document or a file of the repository, linked in the story (`docs/APP.md`,
  `docs/MODELING.md`, `docs/AB_TESTING.md`, `docs/DRIFT_MONITORING.md`,
  `app/schemas.py`, `app/main.py`). Nothing is invented to fill a story.
- **Honest status:** a criterion that is not built is marked ⬜ in its story
  (feedback form in the app, presentations), and a section lists what the system
  does not cover (authentication, batch predictions, GIS input).

## Acceptance criteria

- [ ] `docs/USER_STORIES.md` lists the users and the story format.
- [ ] Every story has its user, goal, benefit, acceptance criteria, level, issues and status.
- [ ] Every story points to the issues that implement it and to the document where the result is recorded.
- [ ] Missing features are marked as not built.
- [ ] `README.md` and `docs/DELIVERABLES.md` link the document.

## Verification

- Every relative link and anchor of `docs/USER_STORIES.md` resolves against
  `develop` (checked with a script).
- Each number in the criteria was compared with the document it comes from
  (`docs/MODELING.md`, `docs/DELIVERABLES.md`, `docs/APP.md`).
- The statuses follow `develop` on 2026-11-18: #28, #31 and #42 are merged and #39 is
  the only implementation issue still open.