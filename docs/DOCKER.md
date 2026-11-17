# Docker usage

How to run the project with Docker and Docker Compose, what each service and
volume does, and what to do when something fails. Ticket #47. For the full
clean-clone procedure (dataset, model export, pinned environment) see
[REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## Quick start

Requirements: Docker with Compose v2.24 or newer (the compose file uses an
`env_file` entry with `required: false`, which older versions reject).

```bash
docker compose up --build      # first build took about three minutes on our test machine
```

When it settles, `docker compose ps` shows `app` running and `db` healthy, and
the Streamlit page is at <http://localhost:8501> (still the M0 placeholder).
Stop it with `Ctrl+C`, or `docker compose down` if you started it with `-d`.

The FastAPI service is **not** part of Compose yet (a permanent `api` service is
tracked in #38). To start it, export the model once and run the API in a
one-off container:

```bash
docker compose exec app python src/export_model.py
docker compose run --rm -p 8000:8000 app uvicorn app.api:app --host 0.0.0.0 --port 8000
```

The export needs `data/raw/covtype.data` on your machine (see
[REPRODUCIBILITY.md](REPRODUCIBILITY.md)). The API is then at
<http://localhost:8000> (Swagger at `/docs`).

## Services

Defined in `docker-compose.yml`.

| Service | Container | Image | Host port | What it does |
|---|---|---|---|---|
| `app` | `multiclass_app` | Built from the `Dockerfile` | 8501 | Runs `streamlit run app/main.py`. It is also the container where you run the project scripts and the API. Starts only after `db` is healthy. |
| `db` | `multiclass_db` | `mysql:8.0` | `${MYSQL_PORT:-3306}` | MySQL for the `predictions` and `feedback` tables (#37). |

- Both services use `restart: unless-stopped`, so they come back after a Docker
  restart until you run `docker compose down`.
- **Health check of `db`:** `mysqladmin ping` over TCP every 5 seconds, up to 10
  retries. TCP is used on purpose: the temporary server of MySQL's first start
  only listens on a socket and must not count as healthy. The first start of an
  empty volume takes around 20 seconds.
- The container names are fixed (`multiclass_app`, `multiclass_db`), so only one
  copy of the stack can exist at a time on a machine.
- Compose names the project after the folder (`verify46` for a clone in
  `verify46/`). The image (`<folder>-app`) and the volume (`<folder>_db_data`)
  follow that name, so another folder gets its own database.

## Volumes

| Mount | Inside the container | Content |
|---|---|---|
| `./app` | `/app/app` | API and Streamlit code. Edits on your machine show up at once. |
| `./src` | `/app/src` | Training, data and database modules. Same live behavior. |
| `./data` | `/app/data` | The dataset in `data/raw/`, `data/processed/new_samples.csv` and the SQLite file used when no MySQL is configured. |
| `./models` | `/app/models` | `model.joblib` and `model_metadata.json` written by `src/export_model.py`. |
| `db_data` (named volume) | `/var/lib/mysql` | The MySQL files. It survives `docker compose down`; `down -v` deletes it. |

`data/raw/`, `data/processed/` and `models/` are git-ignored, so what you see
there is yours alone. Everything else (`scripts/`, `requirements.txt`, the rest
of the repository) is copied into the image at build time and is **not**
mounted: a change to `scripts/` needs a rebuild, a change to `app/` or `src/`
does not.

Streamlit reloads on its own when `app/` changes. The API started with the
command above does not (it has no `--reload`), so restart it after changing
`app/` or `src/`.

## Environment variables

Compose reads a `.env` file next to `docker-compose.yml` if it exists (copy
`.env.example`; it is optional and git-ignored). The defaults are for local use
only; change every password before any shared or cloud deployment (#39).

| Variable | Default | Used by | Purpose |
|---|---|---|---|
| `MYSQL_ROOT_PASSWORD` | `root` | `db` | Root password (also used by the health check). |
| `MYSQL_DATABASE` | `multiclass` | `db` | Database created on the first start. |
| `MYSQL_USER` / `MYSQL_PASSWORD` | `app` / `app` | `db` | Application user created on the first start. |
| `MYSQL_PORT` | `3306` | host | Host port published for MySQL. Set it when 3306 is taken. |
| `DATABASE_URL` | `mysql+pymysql://app:app@db:3306/multiclass` | `app` | Where `src/database.py` connects. Inside Compose the host is `db`, always port 3306. |
| `MODEL_PATH` | `models/model.joblib` | `app` | Model file loaded by the API. |

## The image

Built from the `Dockerfile`:

1. `python:3.11-slim`, the version of `.python-version`.
2. `libgomp1`, which LightGBM needs.
3. `requirements.txt` is copied and installed **before** the rest of the code,
   so editing code does not reinstall the libraries.
4. The repository is copied, and the container runs Streamlit on port 8501.

`.dockerignore` keeps `.git`, `.env`, `data/`, `models/`, `docs/`, `*.md` and
model files out of the image. So the image holds no dataset, no model and no
secrets; Compose supplies the first two through the mounts above. Running the
image on its own (`docker run`) therefore has no data or model.

## Everyday commands

```bash
docker compose up -d --build        # start in the background, rebuilding if needed
docker compose ps -a                # state of both services, including stopped ones
docker compose logs -f app          # follow the app logs (use `db` for MySQL)
docker compose exec app bash        # a shell in the app container
docker compose exec app python scripts/check_imports.py
docker compose exec db mysql -u app -papp multiclass -e "SELECT COUNT(*) FROM predictions"
docker compose down                 # stop and remove the containers, keep the database
docker compose down -v              # same, and delete the database volume
docker compose build --no-cache     # rebuild every layer from scratch
```

## Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine` | Docker Desktop is not running (Windows). | Start Docker Desktop and wait for "Engine running". `docker info` must print a server version. |
| `ports are not available: exposing port TCP 0.0.0.0:3306 ... Only one usage of each socket address` | Another program uses 3306, for example a local MySQL service. | Set `MYSQL_PORT=3307` in `.env` or in the shell, then `docker compose up`. The app is not affected: it reaches the database over Compose's internal network. |
| Same error for port `8501` | Something else uses the Streamlit port. | Stop it, or change the left side of `"8501:8501"` in your copy of `docker-compose.yml` (do not commit that change). |
| `Conflict. The container name "/multiclass_db" is already in use by container ...` (it can name `/multiclass_app` too) | Another copy of the project (or an old stack) holds the fixed names. | Run `docker compose down` in that copy, or `docker rm -f multiclass_app multiclass_db`. The failed attempt leaves an empty network and volume for its own folder; `docker compose down -v` there removes them. |
| `service "app" is not running` after `exec` | `db` failed to start, so `app` was created but never started. | `docker compose ps -a`, then `docker compose logs db`; fix the cause (usually a port, see above). |
| `/health` returns `model_loaded: false` | `models/model.joblib` is missing or invalid; `detail` says why. | `docker compose exec app python src/export_model.py` (needs `data/raw/covtype.data`). |
| `/health` returns `db_connected: false`, or `db` is not healthy | MySQL is still starting, or it failed. | Wait about 20 seconds on a first start; otherwise `docker compose logs db`. `/predict` still answers, with `prediction_id: null`. |
| MySQL rejects the login after you changed `MYSQL_*` in `.env` | MySQL reads those variables only when it creates an empty volume. | `docker compose down -v` to recreate the volume (this deletes the stored rows), and keep `DATABASE_URL` consistent. |
| New libraries are missing after editing `requirements.txt` | The image was built before the change. | `docker compose up --build`. |
| `data/raw/covtype.data` not found inside the container | The dataset is not on your machine. | Download it as in [REPRODUCIBILITY.md](REPRODUCIBILITY.md) and place it in `data/raw/`. |
| `unknown flag` or a complaint about `env_file` / `required` | Compose older than v2.24, or the old `docker-compose` v1. | Update Docker; use `docker compose`, not `docker-compose`. |

## Known limits

- The API is started by hand (see Quick start); there is no `api` service yet (#38).
- The Streamlit page is the M0 placeholder; the prediction form is #33.
- The mounts are for development. A cloud deployment (#39) should build the
  code into the image instead of mounting it.
