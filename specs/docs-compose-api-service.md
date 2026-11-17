# Spec: docs/compose-api-service

| | |
|---|---|
| Issue | none (follow-up of #38, after the reviews of PR #104 and PR #105) |
| Milestone | M7 |
| Branch | `docs/compose-api-service` (from `develop`) |
| Owner | @Leandroletoile |
| Depends on | #38 (`api` service, merged), #47 (Docker guide, merged), #46 (reproducibility guide, merged) |

## Goal

Bring `docs/DOCKER.md` and `docs/REPRODUCIBILITY.md` in line with the `api`
service added by #38. They still said that the API is started by hand with
`docker compose run --rm -p 8000:8000 ...`, a command that now fails because the
`api` service already publishes port 8000. Also document what #38 did not cover:
the API loads the model only at startup. The Usage section of `docs/APP.md` had
the same problem and was fixed in #105; this change only adds `API_URL` there.

## Scope

- In scope: `docs/DOCKER.md`, `docs/REPRODUCIBILITY.md`, two stale lines of
  `docs/DELIVERABLES.md`, the `API_URL` rows of
  `docs/APP.md`, this spec, and the living guide
  (`docs/GUIA_PROYECTO_CLASIFICACION.md`, new D10.9 and a fix in D10.8).
- Out of scope: any change to `docker-compose.yml`, the `Dockerfile` or the code,
  and `README.md` (its final version is #43).

## Design

| File | Change |
|---|---|
| `docs/DOCKER.md` | Quick start, services, health check, volumes, environment variables, image, commands, troubleshooting and known limits cover `api`; restart after exporting the model. |
| `docs/REPRODUCIBILITY.md` | Replace the one-off API container with `docker compose restart api`; update the checklist and known limits. |
| `docs/APP.md` | Document `API_URL` (the Usage section was already fixed in #105). |
| `docs/DELIVERABLES.md` | The Dockerization entries no longer say that the orchestration is tracked in #38; link `docs/DOCKER.md`. |
| `docs/GUIA_PROYECTO_CLASIFICACION.md` | New D10.9 (#38); D10.8 lists the three services. |

Decision: the restart step is documented instead of changing the code, because
loading the model once at startup is the behavior of #34. A reload endpoint
would be a code change for its own ticket.

## Acceptance criteria

- [x] No page tells the reader to start the API with `docker compose run`, or says that the `api` service does not exist.
- [x] `docs/DOCKER.md` covers `api` in services, health check, volumes, variables, commands and troubleshooting.
- [x] The restart after a model export is documented wherever the export is.
- [x] Every relative link of the changed pages resolves.

## Verification

```bash
git grep -n -E "run --rm -p 8000|tracked in #38|no .api. service|not published|Compose does not start" -- docs
```

Expected: no output. Plus a link check of the three pages.

Result (2026-11-17, Windows with Docker Desktop, Compose v5.7.0), run on `develop` at 421aad2:

- `docker compose up -d --build` with no model: `db` healthy in 8.4 s, `api` healthy in 13.1 s, `app` started. `/health` returned `model_loaded: false` and `db_connected: true`.
- After `docker compose exec app python src/export_model.py` (accuracy 0.9520, macro F1 0.9186, 136.3 MB), `/health` still returned `model_loaded: false`: the API loads the model only at startup.
- After `docker compose restart api`, the API did not answer for the first 30 s (`health: starting`, connection closed). Loading the model takes 20 to 40 seconds.
- `docker compose up -d` with the model present: the three services came up in 29 s (`api` healthy at 27.3 s). `/health` returned `model_loaded: true` and `db_connected: true`. `POST /predict` with the example of `docs/APP.md` returned `cover_type` 2 (Lodgepole Pine), confidence 0.95, `prediction_id` 1.
- `git grep` for the old statements finds nothing in `docs/`, and the relative links of the five changed pages resolve.
- Not run here: the port 8000 conflict row and `docker rm -f` with the three container names.