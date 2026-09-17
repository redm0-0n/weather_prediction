from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "models" / "model.pkl"

artifact = joblib.load(MODEL_PATH)
model = artifact["model"]
feature_names = artifact["features"]
target_name = artifact["target"]
prediction_horizon = artifact.get("prediction_horizon_hours", 3)


class PredictionRequest(BaseModel):
    features: dict[str, float]


app = FastAPI(
    title="Innopolis Weather Prediction API",
    description="Temperature prediction for Innopolis three hours ahead",
    version="1.0.0",
)


@app.get("/")
def root():
    return {"message": "Weather prediction API", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": True,
        "number_of_features": len(feature_names),
    }


@app.get("/model-info")
def model_info():
    return {
        "target": target_name,
        "prediction_horizon_hours": prediction_horizon,
        "number_of_features": len(feature_names),
        "features": feature_names,
    }


@app.post("/predict")
def predict(request: PredictionRequest):
    missing = set(feature_names) - set(request.features)
    extra = set(request.features) - set(feature_names)

    if missing or extra:
        raise HTTPException(
            status_code=422,
            detail={
                "missing_features": sorted(missing),
                "unexpected_features": sorted(extra),
            },
        )

    values = {
        feature: request.features[feature]
        for feature in feature_names
    }
    prediction = model.predict(pd.DataFrame([values]))[0]

    return {
        "predicted_temperature": float(prediction),
        "prediction_horizon_hours": prediction_horizon,
        "target": target_name,
    }
