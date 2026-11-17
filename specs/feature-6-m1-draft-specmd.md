# Spec: feature/6-m1-draft-specmd

| | |
|---|---|
| Issue | #6 - [M1] Draft SPEC.md (functional and technical specification) |
| Milestone | M1 |
| Branch | `feature/6-m1-draft-specmd` (from `develop`) |
| Owner | @nagicome03 |
| Depends on | #2 (problem definition, merged), #3 (dataset selection, merged) |

## Goal

Complete `SPEC.md` so it is a functional and technical specification consistent
with the current `README.md`, with the architecture clearly described and the
requirements linked to the delivery levels.

## Scope

- In scope: `SPEC.md` — fill the functional and technical requirements,
  describe the architecture (Streamlit -> FastAPI -> model -> DB), add a
  delivery-levels section aligned with the README, and resolve the stale
  dataset "source & version" placeholder.
- Out of scope:
  - `README.md` completion (#43).
  - `requirements.txt` pinning and run steps (#46).
  - Technical report and presentations (M7 / M8).

## Design

| File | Change |
|---|---|
| `SPEC.md` | Fill sections 4 (functional) and 5 (technical), describe the architecture (section 6), add a delivery-levels section (7) and renumber quality gates (8). |

Decisions and reasons:

- **Consistent with the README.** The README is the entry point and already
  lists the tech stack, delivery levels and repository structure; SPEC.md is
  aligned to it rather than redefining terms.
- **Architecture.** Streamlit (frontend) -> FastAPI (backend) -> exported model
  pipeline -> prediction, with MySQL for feedback persistence and a retraining
  pipeline, matching `src/export_model.py`, `src/retraining.py` and
  `src/database.py`.
- **Delivery levels.** Mirrors the four README levels (Esencial / Medio /
  Avanzado / Experto) and maps each one to the concrete project elements.

## Acceptance criteria

Copied from issue #6:

- [ ] SPEC.md complete and consistent with the README
- [ ] Architecture clearly described

## Verification

Read `SPEC.md` and confirm: sections 4-6 are filled, the architecture is
described in words and a diagram, the delivery levels are linked, and the
content does not contradict `README.md`.
