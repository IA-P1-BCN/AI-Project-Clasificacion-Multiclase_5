"""Request and response schemas of the prediction API (ticket #34)."""
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