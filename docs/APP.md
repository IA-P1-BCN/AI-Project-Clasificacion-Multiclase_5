# APP — Application Requirements

> Requirements and design of the prediction application.

## Functional requirements

- Accepts input data and returns a multiclass prediction.
- Streamlit (frontend) + FastAPI (backend) + model pipeline.
- Feedback collection system to monitor production performance.
- Pipeline to collect new data for future retraining.

## Architecture

```
Streamlit (frontend) ──► FastAPI (backend) ──► model pipeline ──► prediction
                              │
                              ▼
                        Database (MySQL/MongoDB)
```

## Dockerization

- `Dockerfile` + `docker-compose.yml`
- Services: app (backend + frontend), database (optional)

## Deployment

- Cloud target: Render / Vercel / AWS (to be decided in M6).

## Usage

```bash
docker compose up
```

_To be filled in M6._
