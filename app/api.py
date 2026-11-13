"""FastAPI backend (ticket #34): serve the trained model over HTTP.

Run from the project root: `uvicorn app.api:app --port 8000`
Interactive documentation: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.schemas import PredictionRequest, PredictionResponse
from app.serving import MODEL_PATH, load_model, predict


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model once at startup. A missing model does not stop the API."""
    app.state.loaded = load_model(MODEL_PATH)
    yield


app = FastAPI(
    title="Covertype classification API",
    description="Predicts the forest cover type (1-7) of a 30 x 30 m cell.",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    """Service status and whether a model is loaded."""
    loaded = app.state.loaded
    return {"status": "ok", "model_loaded": loaded.ready, "detail": loaded.error}


@app.post("/predict", response_model=PredictionResponse)
def predict_cover_type(request: PredictionRequest) -> dict:
    """Validate the input and return the predicted cover type with its confidence."""
    loaded = app.state.loaded
    if not loaded.ready:
        raise HTTPException(status_code=503, detail=loaded.error)
    return predict(loaded, request)