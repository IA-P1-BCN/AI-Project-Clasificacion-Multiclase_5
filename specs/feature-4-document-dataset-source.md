# Spec: feature/4-document-dataset-source

| | |
|---|---|
| Issue | #4 - [M1] Download the original dataset and document source + version |
| Milestone | M1 |
| Branch | `feature/4-document-dataset-source` (from `develop`) |
| Owner | @levifvy |
| Depends on | M1 dataset selection (done: Covertype) |

## Goal

Record where the raw dataset comes from and which exact file we use, so that
any teammate can download the same data and check that it is identical.

## Scope

- In scope: `data/README.md` (source URL, version, download date, size,
  checksum, download and verification steps); a link from the root README.
- Out of scope: `SPEC.md` section 3 ("Source & version: to be documented"),
  which is being rewritten in the open Pull Request #57 (issue #2).

## Design

| File | Change |
|---|---|
| `data/README.md` | New. Tracked by Git: `.gitignore` only ignores the contents of `data/raw/` and `data/processed/`. |
| `README.md` | Link to `data/README.md` from the *Dataset* section and the repository tree. |

Decisions:

- UCI does not publish numbered versions, so the file is identified by its
  SHA-256 checksum and size in addition to the donation date.
- The raw file stays untracked (75 MB; `data/raw/*` is git-ignored).

## Acceptance criteria

- [x] Download the original dataset from the official source
- [x] Save it under `data/raw/` (untracked)
- [x] Record source URL, version and download date in a data README
- [x] Add checksum/size note
- [x] Another person can re-download from the documented source

## Verification

Run on 2026-11-12:

| Check | Result |
|---|---|
| `curl -L https://archive.ics.uci.edu/static/public/31/covertype.zip` | HTTP 200, archive contains `covtype.data.gz`, `covtype.info`, `old_covtype.info` |
| SHA-256 of the freshly downloaded and decompressed `covtype.data` | `0a9371ce...96217945`, identical to the local `data/raw/covtype.data` |
| `git status --short data/` | Only `data/README.md` is new; nothing under `data/raw/` is tracked |
