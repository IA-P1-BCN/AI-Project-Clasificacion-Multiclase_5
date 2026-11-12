# Spec: feature/m0-dev-environment-config

| | |
|---|---|
| Issue | none (environment) |
| Milestone | M0 |
| Branch | `feature/m0-dev-environment-config` (from `develop`) |
| Owner | @levifvy |
| Depends on | none |

## Goal

Keep local development configuration out of the task branches: ignore IDE
files and make the dataset and the trained models visible inside the container.

## Scope

- In scope: `.gitignore`, `docker-compose.yml`.
- Out of scope: the `Dockerfile`, the commented database service, any code.

## Design

| File | Change | Reason |
|---|---|---|
| `.gitignore` | Ignore `.idea/`, `*.iml`, `*.iws`, `*.ipr` | PyCharm / IntelliJ project files are machine-specific |
| `docker-compose.yml` | Mount `./data` at `/app/data` and `./models` at `/app/models` | Both folders are git-ignored and excluded from the image, so without the mounts the container cannot read `data/raw/covtype.data` or write model artifacts |

## Acceptance criteria

- [x] No file under `.idea/` is tracked
- [x] `docker compose config` accepts the file and lists the two new mounts

## Verification

- `git ls-files .idea` returns nothing.
- `docker compose config` run on 2026-11-12: valid, binds `./data` -> `/app/data` and `./models` -> `/app/models`.
