"""FastAPI backend (tickets #34, #37, #35): serve the model, persist predictions, collect feedback.

Run from the project root: `uvicorn app.api:app --port 8000`
Interactive documentation: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
import logging
import os

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
import pandas as pd

from app.schemas import (
    ABResultsResponse,
    DriftResponse,
    FeedbackRequest,
    FeedbackResponse,
    MetricsResponse,
    PredictionRequest,
    PredictionResponse,
)
from app.serving import MODEL_B_PATH, MODEL_PATH, load_model, predict
from ab_testing import MODEL_VERSIONS, build_report, choose_variant, traffic_share_b
from database import (
    ab_metrics,
    db_status,
    feedback_metrics,
    get_prediction,
    init_db,
    prediction_inputs,
    save_feedback,
    save_prediction,
)
from drift_monitoring import (
    MIN_ROWS,
    PSI_ALERT,
    PSI_WARNING,
    WINDOW_SIZE,
    check_and_alert,
    drift_check_every,
    load_reference,
    windows_report,
)
from target_encoding import CLASS_NAMES

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model and initialize the database once at startup."""
    app.state.loaded = load_model(MODEL_PATH)
    # A/B test (#52): the challenger is optional and the split defaults to 0 (all traffic to A).
    app.state.loaded_b = load_model(MODEL_B_PATH)
    try:
        app.state.share_b = traffic_share_b()
    except ValueError as exc:
        logger.warning("%s The A/B test is disabled.", exc)
        app.state.share_b = 0.0
    if app.state.share_b > 0 and not app.state.loaded_b.ready:
        logger.warning("AB_TRAFFIC_B > 0 but model B is not available: %s", app.state.loaded_b.error)
    # Data drift monitoring (#53): needs the reference profile (python src/drift_monitoring.py build).
    app.state.drift_check_every = drift_check_every()
    try:
        app.state.drift_reference = load_reference()
        app.state.drift_error = None
    except Exception as exc:  # monitoring is optional: the API serves predictions without it
        app.state.drift_reference = None
        app.state.drift_error = str(exc)
        logger.warning("Drift monitoring is off: %s", exc)
    try:
        init_db()
    except Exception as exc:  # a missing or unreachable DB must not stop the API from starting
        logger.warning("Database not available at startup: %s", exc)
    yield


app = FastAPI(
    title="Covertype classification API",
    description="Predicts the forest cover type (1-7) of a 30 x 30 m cell.",
    lifespan=lifespan,
)


def drift_check_due(prediction_id) -> bool:
    """True when a drift check is due after storing prediction `prediction_id` (#53)."""
    every = app.state.drift_check_every
    return (
        prediction_id is not None
        and app.state.drift_reference is not None
        and every > 0
        and prediction_id % every == 0
    )


def run_drift_check() -> None:
    """Background task: check the latest window of predictions and alert on drift. Never raises."""
    try:
        rows = pd.DataFrame(prediction_inputs(limit=WINDOW_SIZE))
        check_and_alert(app.state.drift_reference, rows, WINDOW_SIZE, os.getenv("DRIFT_WEBHOOK_URL"))
    except Exception as exc:  # a monitoring failure must not affect the API
        logger.warning("Drift check failed: %s", exc)


@app.get("/health")
def health() -> dict:
    """Service status, whether a model is loaded, and database connectivity."""
    loaded = app.state.loaded
    db = db_status()
    return {
        "status": "ok",
        "model_loaded": loaded.ready,
        "db_connected": db["connected"],
        "detail": loaded.error,
        "db_detail": db["error"],
        "ab_test": {
            "enabled": app.state.share_b > 0 and app.state.loaded_b.ready,
            "traffic_b": app.state.share_b,
            "model_b_loaded": app.state.loaded_b.ready,
            "detail_b": app.state.loaded_b.error,
        },
        "drift": {
            "enabled": app.state.drift_reference is not None,
            "window": WINDOW_SIZE,
            "check_every": app.state.drift_check_every,
            "webhook": bool(os.getenv("DRIFT_WEBHOOK_URL")),
            "detail": app.state.drift_error,
        },
    }


@app.post("/predict", response_model=PredictionResponse)
def predict_cover_type(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    variant: str | None = Query(
        default=None, description="Force the A/B variant ('A' or 'B'); by default the traffic split decides."
    ),
) -> dict:
    """Validate the input, return the predicted cover type, and persist the prediction.

    The request is served by variant A (control) or B (challenger) according to
    AB_TRAFFIC_B (#52); the variant is stored with the prediction.
    """
    try:
        chosen = choose_variant(app.state.share_b, app.state.loaded_b.ready, forced=variant)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    loaded = app.state.loaded_b if chosen == "B" else app.state.loaded
    if not loaded.ready:
        raise HTTPException(status_code=503, detail=loaded.error)
    result = predict(loaded, request)
    result["variant"] = chosen
    try:
        result["prediction_id"] = save_prediction(
            request, result, model_version=MODEL_VERSIONS[chosen], variant=chosen
        )
    except Exception as exc:  # the prediction is still returned when the DB is down
        logger.warning("Prediction not persisted: %s", exc)
        result["prediction_id"] = None
    if drift_check_due(result["prediction_id"]):  # data drift monitoring (#53)
        background_tasks.add_task(run_drift_check)
    return result


@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest) -> dict:
    """Store the observed Cover_Type for a past prediction and report whether it was correct."""
    try:
        prediction = get_prediction(request.prediction_id)
    except Exception as exc:  # database unreachable
        raise HTTPException(status_code=503, detail=f"Feedback not stored: {exc}") from exc
    if prediction is None:
        raise HTTPException(
            status_code=404, detail=f"Prediction id={request.prediction_id} does not exist."
        )

    try:
        feedback_id = save_feedback(
            request.prediction_id, request.true_cover_type, request.comment
        )
    except Exception as exc:  # database became unreachable between the read and the write
        raise HTTPException(status_code=503, detail=f"Feedback not stored: {exc}") from exc

    predicted_cover_type = int(prediction["predicted_cover_type"])
    return {
        "feedback_id": feedback_id,
        "prediction_id": request.prediction_id,
        "true_cover_type": request.true_cover_type,
        "true_class_name": CLASS_NAMES[request.true_cover_type],
        "predicted_cover_type": predicted_cover_type,
        "is_correct": predicted_cover_type == request.true_cover_type,
    }


@app.get("/metrics", response_model=MetricsResponse)
def production_metrics() -> dict:
    """Basic production-monitoring metrics aggregated from stored predictions and feedback."""
    try:
        return feedback_metrics()
    except Exception as exc:  # database unreachable
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/ab/results", response_model=ABResultsResponse)
def ab_results() -> dict:
    """A/B test (#52): metrics of each variant and the winner decision."""
    try:
        return build_report(ab_metrics())
    except Exception as exc:  # database unreachable
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/drift", response_model=DriftResponse)
def drift(
    windows: int = Query(default=5, ge=1, le=20, description="Number of windows to report, latest last."),
) -> dict:
    """Data drift (#53): PSI of the stored inputs against the training data, by window of predictions."""
    reference = app.state.drift_reference
    if reference is None:
        raise HTTPException(status_code=503, detail=app.state.drift_error)
    try:
        rows = pd.DataFrame(prediction_inputs(limit=WINDOW_SIZE * windows))
    except Exception as exc:  # database unreachable
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    reported = (
        windows_report(reference, rows, WINDOW_SIZE, n_windows=windows)["windows"] if not rows.empty else []
    )
    latest = reported[-1] if reported else None
    return {
        "status": latest["status"] if latest else "insufficient_data",
        "window_size": WINDOW_SIZE,
        "thresholds": {"warning": PSI_WARNING, "alert": PSI_ALERT, "min_rows": MIN_ROWS},
        "reference": {"n_rows": reference["n_rows"], "created_at_utc": reference["created_at_utc"]},
        "latest": latest,
        "history": reported[:-1],
    }
