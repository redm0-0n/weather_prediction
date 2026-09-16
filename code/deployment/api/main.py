import math
from pathlib import Path
from typing import Any
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "models" / "model.pkl"

def load_model_artifact() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file was not found: {MODEL_PATH}. "
            "Run 'dvc repro' before starting the API."
        )

    artifact = joblib.load(MODEL_PATH)
    required_keys = {"model", "features", "target"}
    if not isinstance(artifact, dict):
        raise ValueError(
            "The model artifact must be a dictionary containing "
            "the model and its metadata."
        )

    missing_keys = required_keys - set(artifact)
    if missing_keys:
        raise ValueError(
            f"Model artifact is missing keys: {sorted(missing_keys)}"
        )

    return artifact

MODEL_ARTIFACT = load_model_artifact()
MODEL = MODEL_ARTIFACT["model"]
FEATURE_NAMES = MODEL_ARTIFACT["features"]
TARGET_NAME = MODEL_ARTIFACT["target"]
PREDICTION_HORIZON = MODEL_ARTIFACT.get("prediction_horizon_hours", 3)

class PredictionRequest(BaseModel):
    features: dict[str, float] = Field(
        ...,
        description=(
            "Dictionary containing all weather features required "
            "by the model."
        ),
    )

    @field_validator("features")
    @classmethod
    def validate_finite_values(cls, features: dict[str, float]) -> dict[str, float]:
        invalid_features = [name for name, value in features.items() if not math.isfinite(value)]
        if invalid_features:
            raise ValueError(
                "Feature values must be finite. Invalid features: "
                f"{sorted(invalid_features)}"
            )
        return features

class PredictionResponse(BaseModel):
    predicted_temperature: float
    prediction_horizon_hours: int
    target: str

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    number_of_features: int

class ModelInfoResponse(BaseModel):
    target: str
    prediction_horizon_hours: int
    number_of_features: int
    features: list[str]

app = FastAPI(
    title="Innopolis Weather Prediction API",
    description=(
        "API for predicting the temperature in Innopolis "
        "three hours ahead."
    ),
    version="1.0.0",
)

@app.get("/")
def root():
    return {
        "message": "Innopolis Weather Prediction API",
        "documentation": "/docs",
        "health": "/health",
        "model_info": "/model-info",
    }

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        model_loaded=True,
        number_of_features=len(FEATURE_NAMES),
    )

@app.get("/model-info", response_model=ModelInfoResponse)
def model_info():
    return ModelInfoResponse(
        target=TARGET_NAME,
        prediction_horizon_hours=PREDICTION_HORIZON,
        number_of_features=len(FEATURE_NAMES),
        features=FEATURE_NAMES,
    )

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    received_features = set(request.features)
    required_features = set(FEATURE_NAMES)
    missing_features = required_features - received_features
    unexpected_features = received_features - required_features

    if missing_features or unexpected_features:
        error_details = {}

        if missing_features:
            error_details["missing_features"] = sorted(missing_features)
        if unexpected_features:
            error_details["unexpected_features"] = sorted(unexpected_features)
        raise HTTPException(
            status_code=422,
            detail=error_details,
        )

    ordered_features = {feature: request.features[feature] for feature in FEATURE_NAMES}
    input_df = pd.DataFrame([ordered_features])

    try:
        prediction = MODEL.predict(input_df)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Model prediction failed: {error}",
        ) from error

    return PredictionResponse(
        predicted_temperature=float(prediction[0]),
        prediction_horizon_hours=PREDICTION_HORIZON,
        target=TARGET_NAME,
    )