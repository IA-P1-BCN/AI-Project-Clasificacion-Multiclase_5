"""FastAPI backend (ticket #34, #37): serve the trained model over HTTP and persist predictions.

Run from the project root: `uvicorn app.api:app --port 8000`
Interactive documentation: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.schemas import PredictionRequest, PredictionResponse
from app.serving import MODEL_PATH, load_model, predict
from database import db_status, init_db, save_prediction


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model and initialize the database once at startup."""
    app.state.loaded = load_model(MODEL_PATH)
    try:
        init_db()
    except Exception:
        pass  # A missing or unreachable DB must not stop the API from starting
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
    except Exception:
        result["prediction_id"] = None
    return result
