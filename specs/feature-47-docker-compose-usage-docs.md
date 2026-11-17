# Spec: feature/47-docker-compose-usage-docs

| | |
|---|---|
| Issue | #47 - [M7] Docker/compose usage docs |
| Milestone | M7 |
| Branch | `feature/47-docker-compose-usage-docs` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | M6 Docker (`Dockerfile` and `docker-compose.yml` in `develop`) |

## Goal

One page that tells anyone how to run the project with Docker: the commands, what
each service and volume is for, and what to do for the failures we have seen.

## Scope

- In scope:
  - New `docs/DOCKER.md`: quick start (`docker compose up`), services, volumes,
    environment variables, the image, everyday commands, troubleshooting and
    known limits.
  - Links to it from `README.md` and `docs/REPRODUCIBILITY.md`.
  - Check every statement of the page against the repository or an observed run.
- Out of scope:
  - Any change to `Dockerfile` or `docker-compose.yml` (the `api` service and the
    multi-process orchestration are #38).
  - The full clean-clone procedure and the pinned environment (done in #46).
  - `docs/APP.md` (its Dockerization and Usage sections are being rewritten in
    PR #97 of #45; a link to the new page can follow once it merges).
  - Cloud deployment (#39).

## Design

| File | Change |
|---|---|
| `docs/DOCKER.md` | New. |
| `README.md` | One line in the Setup section and the new page in the repository tree. |
| `docs/REPRODUCIBILITY.md` | A link in step 2, where the Docker path starts. |

Decisions and reasons:

- **A separate page, not more text in `REPRODUCIBILITY.md`.** That page is a
  linear procedure to reproduce the project once; this one is a reference to come
  back to (what a volume holds, why a port fails). Each links to the other.
- **Troubleshooting lists what we actually hit,** in the order they appeared in
  the #46 clean-clone run: Docker Desktop not running, port 3306 taken by a local
  MySQL, `exec` on a service that never started. The rest are standard behavior of
  Docker, Compose and the MySQL image, listed with the exact message when we know it.
- **The API is documented as a one-off `docker compose run -p`,** because Compose
  publishes only port 8501. This is the command checked in #46.
- **No change to the compose file here.** A documentation ticket should describe
  the files as they are; changes belong to #38.

## Acceptance criteria

Copied from issue #47:

- [x] Docker usage documented
- [x] `docker compose up` documented
- [x] Services and volumes described
- [x] Troubleshooting notes added

## Verification

1. Every relative link of `docs/DOCKER.md`, and the links added to `README.md`
   and `docs/REPRODUCIBILITY.md`, point to an existing file.
2. Commands of the page run on a machine with Docker Desktop: `docker compose
   version`, `docker compose up -d --build`, `docker compose ps -a`, `docker
   compose exec db mysql -u app -papp multiclass -e "SELECT COUNT(*) FROM
   predictions"`, `docker compose exec app python scripts/check_imports.py`,
   `docker compose down`.
3. Start a second copy of the stack while the first is up and confirm the
   container-name conflict message.
4. `docker compose config` shows `MYSQL_PORT` honored.

Result (2026-11-17, Windows with Docker Desktop, Compose v5.5.1):

- Every relative link of `docs/DOCKER.md` points to an existing file.
- `docker compose up -d --build`: `app` started and `db` was healthy in 16 s. The published ports are 8501 and, with `MYSQL_PORT=3307`, 3307. The image and the volume are named after the folder, as the page says.
- `src/database.py` inside the container: checks passed and MySQL connected. `SELECT COUNT(*) FROM predictions` returned 0 on a new volume.
- `scripts/check_imports.py` inside the container: all 27 modules import.
- `docker compose config` shows `published: "3307"` with the variable set.
- A second copy of the stack started while the first was up failed with `Conflict. The container name "/multiclass_db" is already in use by container ...`; the table uses that message. The attempt left an empty network and volume, removed with `docker compose down -v`.
- Seen earlier in the #46 clean-clone run: Docker Desktop not running, port 3306 taken by a local MySQL, and `exec` on a service that never started.
- Not run here: `exec app bash`, `logs -f`, `build --no-cache`, the port 8501 conflict, and the rows that describe standard Docker, Compose and MySQL behavior (variables read only on an empty volume, Compose 2.24 for `env_file` `required`).