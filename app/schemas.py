"""Request and response schemas of the prediction API (tickets #34, #35)."""
from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    """One observation: the 10 numeric features plus the wilderness area and soil type.

    Numeric fields use the dataset column names (see docs/DATA_DICTIONARY.md).
    The bounds are physical limits, not the observed min/max, so a valid new
    observation is not rejected. The API expands `Wilderness_Area` and
    `Soil_Type` into the 44 one-hot columns the model was trained on.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "Elevation": 2900,
                "Aspect": 150,
                "Slope": 12,
                "Horizontal_Distance_To_Hydrology": 250,
                "Vertical_Distance_To_Hydrology": 40,
                "Horizontal_Distance_To_Roadways": 2300,
                "Hillshade_9am": 215,
                "Hillshade_Noon": 225,
                "Hillshade_3pm": 140,
                "Horizontal_Distance_To_Fire_Points": 1900,
                "Wilderness_Area": 1,
                "Soil_Type": 29,
            }
        },
    )

    Elevation: float = Field(..., ge=0, le=5000, description="Elevation in meters.")
    Aspect: float = Field(..., ge=0, le=360, description="Slope direction in degrees azimuth.")
    Slope: float = Field(..., ge=0, le=90, description="Slope in degrees.")
    Horizontal_Distance_To_Hydrology: float = Field(..., ge=0, le=10000, description="Meters.")
    Vertical_Distance_To_Hydrology: float = Field(
        ..., ge=-500, le=1000, description="Meters; negative below the water level."
    )
    Horizontal_Distance_To_Roadways: float = Field(..., ge=0, le=10000, description="Meters.")
    Hillshade_9am: float = Field(..., ge=0, le=255, description="Index 0-255.")
    Hillshade_Noon: float = Field(..., ge=0, le=255, description="Index 0-255.")
    Hillshade_3pm: float = Field(..., ge=0, le=255, description="Index 0-255.")
    Horizontal_Distance_To_Fire_Points: float = Field(..., ge=0, le=10000, description="Meters.")
    Wilderness_Area: int = Field(..., ge=1, le=4, description="Wilderness area, 1 to 4.")
    Soil_Type: int = Field(..., ge=1, le=40, description="Soil type, 1 to 40.")


class PredictionResponse(BaseModel):
    """Predicted cover type with the model's confidence."""

    cover_type: int = Field(..., description="Predicted Cover_Type, 1 to 7.")
    class_name: str = Field(..., description="Dominant tree species of the predicted class.")
    confidence: float = Field(..., description="Probability of the predicted class.")
    probabilities: dict[str, float] = Field(..., description="Probability of each class by name.")
    prediction_id: int | None = Field(
        default=None,
        description="Database row ID of the logged prediction, or None if persistence was skipped.",
    )
    variant: str = Field(
        default="A",
        description="A/B test variant that served the request: 'A' (control) or 'B' (challenger).",
    )


class FeedbackRequest(BaseModel):
    """Ground-truth feedback for a past prediction (ticket #35).

    `prediction_id` is the id returned by `POST /predict`. `true_cover_type` is
    the observed class (1-7); an out-of-range value is rejected with HTTP 422
    before the database is touched.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"prediction_id": 1, "true_cover_type": 2, "comment": "Verified in the field."}
        },
    )

    prediction_id: int = Field(..., ge=1, description="ID of the prediction being corrected.")
    true_cover_type: int = Field(..., ge=1, le=7, description="Observed Cover_Type, 1 to 7.")
    comment: str | None = Field(default=None, max_length=1000, description="Optional free-text note.")


class FeedbackResponse(BaseModel):
    """Stored feedback with the model's original prediction and whether it was right."""

    feedback_id: int = Field(..., description="Database row ID of the stored feedback.")
    prediction_id: int = Field(..., description="ID of the prediction this feedback refers to.")
    true_cover_type: int = Field(..., description="Observed Cover_Type, 1 to 7.")
    true_class_name: str = Field(..., description="Dominant tree species of the observed class.")
    predicted_cover_type: int = Field(..., description="Cover_Type the model had predicted.")
    is_correct: bool = Field(..., description="Whether the prediction matched the observed class.")


class ClassMetric(BaseModel):
    """Per-class production metrics derived from collected feedback."""

    cover_type: int = Field(..., description="Cover_Type, 1 to 7.")
    class_name: str = Field(..., description="Dominant tree species of the class.")
    feedback_count: int = Field(..., description="Feedback entries whose true class is this one.")
    correct: int = Field(..., description="Of those, how many the model predicted correctly.")
    accuracy: float | None = Field(
        default=None, description="correct / feedback_count, or null if no feedback for this class."
    )


class MetricsResponse(BaseModel):
    """Basic production-monitoring metrics (ticket #35)."""

    predictions_total: int = Field(..., description="Predictions stored so far.")
    feedback_total: int = Field(..., description="Feedback entries stored so far.")
    feedback_coverage: float | None = Field(
        default=None, description="feedback_total / predictions_total, or null if no predictions."
    )
    correct_total: int = Field(..., description="Feedback entries where the prediction was correct.")
    live_accuracy: float | None = Field(
        default=None, description="Accuracy measured on feedback, or null if no feedback yet."
    )
    average_confidence: float | None = Field(
        default=None, description="Mean confidence of predictions that received feedback."
    )
    per_class: list[ClassMetric] = Field(..., description="Per-class feedback metrics, Cover_Type 1 to 7.")


class ABVariantStats(BaseModel):
    """Counts of one variant of the A/B test (ticket #52)."""

    variant: str = Field(..., description="'A' (control) or 'B' (challenger).")
    model_version: str | None = Field(
        default=None, description="Model version stored with the predictions of this variant."
    )
    predictions: int = Field(..., description="Predictions served by this variant.")
    feedback: int = Field(..., description="Labelled feedback entries received for them.")
    correct: int = Field(..., description="Of those, how many the variant predicted correctly.")
    average_confidence: float | None = Field(
        default=None, description="Mean confidence of the predictions that received feedback."
    )
    live_accuracy: float | None = Field(
        default=None, description="correct / feedback, or null if no feedback yet."
    )


class ABRule(BaseModel):
    """Thresholds of the winner decision rule."""

    min_feedback_per_variant: int = Field(..., description="Labelled feedback needed per variant.")
    alpha: float = Field(..., description="Significance level of the two-sided z-test.")
    min_effect: float = Field(..., description="Smallest accuracy difference that counts as a win.")


class ABResultsResponse(BaseModel):
    """A/B test results and decision (ticket #52)."""

    variants: dict[str, ABVariantStats] = Field(..., description="Metrics of variants 'A' and 'B'.")
    decision: str = Field(
        ..., description="winner_A, winner_B, inconclusive or insufficient_data."
    )
    difference: float | None = Field(default=None, description="Accuracy of B minus accuracy of A.")
    z: float | None = Field(default=None, description="z statistic (positive when B is better).")
    p_value: float | None = Field(default=None, description="Two-sided p-value of the z-test.")
    rule: ABRule = Field(..., description="Decision rule applied.")


class DriftFeature(BaseModel):
    """Drift of one monitored input in a window (ticket #53)."""

    psi: float = Field(..., description="Population Stability Index against the training data.")
    level: str = Field(..., description="ok, warning or alert.")


class DriftAlert(BaseModel):
    """A feature whose PSI reached the warning or alert threshold."""

    feature: str = Field(..., description="Name of the input.")
    psi: float = Field(..., description="Its PSI.")
    level: str = Field(..., description="warning or alert.")


class DriftWindow(BaseModel):
    """Summary of one window of consecutive predictions."""

    status: str = Field(..., description="ok, warning, alert or insufficient_data.")
    rows: int = Field(..., description="Predictions in the window.")
    max_psi: float | None = Field(default=None, description="Highest PSI of the window.")
    max_feature: str | None = Field(default=None, description="Input with the highest PSI.")
    first_id: int = Field(..., description="Id of the first prediction of the window.")
    last_id: int = Field(..., description="Id of the last prediction of the window.")
    start_utc: str = Field(..., description="Timestamp of the first prediction.")
    end_utc: str = Field(..., description="Timestamp of the last prediction.")


class DriftLatest(DriftWindow):
    """The latest window with the PSI of every input."""

    features: dict[str, DriftFeature] = Field(..., description="PSI and level of each monitored input.")
    alerts: list[DriftAlert] = Field(..., description="Inputs at warning or alert, highest PSI first.")


class DriftReference(BaseModel):
    """Training profile the live inputs are compared with."""

    n_rows: int = Field(..., description="Training rows the profile was built from.")
    created_at_utc: str = Field(..., description="When the profile was built.")


class DriftResponse(BaseModel):
    """Data drift of the inputs received by the API (ticket #53)."""

    status: str = Field(..., description="Status of the latest window.")
    window_size: int = Field(..., description="Predictions per window.")
    thresholds: dict[str, float] = Field(..., description="PSI thresholds and minimum rows per window.")
    reference: DriftReference = Field(..., description="Training profile used as reference.")
    latest: DriftLatest | None = Field(default=None, description="Latest window, null if there are no predictions.")
    history: list[DriftWindow] = Field(..., description="Previous windows, oldest first.")