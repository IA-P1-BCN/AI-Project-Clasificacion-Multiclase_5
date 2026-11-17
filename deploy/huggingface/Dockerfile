# syntax=docker/dockerfile:1
# Hugging Face Space image (issue #39). Copy this file and README.md (same
# folder) to the root of a Docker Space. The project is cloned from GitHub at
# build time, so the Space repository only holds these two files.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git to clone the project, libgomp1 for lightgbm / xgboost wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as UID 1000; everything it writes must be owned by it
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

# Space *variables* are passed as build args, so the source branch can be
# changed from the Space settings without editing this file.
ARG REPO_URL=https://github.com/IA-P1-BCN/AI-Project-Clasificacion-Multiclase_5.git
ARG REPO_REF=develop
RUN git clone --depth 1 --branch "${REPO_REF}" "${REPO_URL}" . \
    && pip install --user -r requirements.txt

# Runtime configuration read by scripts/start_cloud.py. MODEL_URL and
# MODEL_SHA256 are set as Space variables (see README.md / docs/APP.md).
ENV SERVICE_ROLE=all \
    PORT=7860 \
    API_PORT=8000 \
    API_URL=http://127.0.0.1:8000 \
    MODEL_PATH=/home/user/app/models/model.joblib \
    DATABASE_URL=sqlite:////home/user/app/data/processed/multiclass.db

EXPOSE 7860

CMD ["python", "scripts/start_cloud.py"]
