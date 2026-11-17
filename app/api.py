"""FastAPI backend (tickets #34, #37, #35): serve the model, persist predictions, collect feedback.

Run from the project root: `uvicorn app.api:app --port 8000`
Interactive documentation: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException

from app.schemas import (
    FeedbackRequest,
    FeedbackResponse,
    MetricsResponse,
    PredictionRequest,
    PredictionResponse,
)
from app.serving import MODEL_PATH, load_model, predict
from database import (
    db_status,
    feedback_metrics,
    get_prediction,
    init_db,
    save_feedback,
    save_prediction,
)
from target_encoding import CLASS_NAMES

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model and initialize the database once at startup."""
    app.state.loaded = load_model(MODEL_PATH)
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
    }


@app.post("/predict", response_model=PredictionResponse)
def predict_cover_type(request: PredictionRequest) -> dict:
    """Validate the input, return the predicted cover type, and persist the prediction."""
    loaded = app.state.loaded
    if not loaded.ready:
        raise HTTPException(status_code=503, detail=loaded.error)
    result = predict(loaded, request)
    try:
        result["prediction_id"] = save_prediction(request, result)
    except Exception as exc:  # the prediction is still returned when the DB is down
        logger.warning("Prediction not persisted: %s", exc)
        result["prediction_id"] = None
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
