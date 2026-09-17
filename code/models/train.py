import json
from pathlib import Path
import joblib
import mlflow
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from mlflow import MlflowClient

TRAIN_DATA_PATH = Path("data/processed/train.csv")
TEST_DATA_PATH = Path("data/processed/test.csv")

MODEL_OUTPUT_PATH = Path("models/model.pkl")
METRICS_OUTPUT_PATH = Path("metrics/metrics.json")

TARGET_COLUMN = "target_temperature_3h"
DATETIME_COLUMN = "datetime"

MODEL_PARAMS = {
    "n_estimators": 200,
    "max_depth": 20,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "random_state": 42,
    "n_jobs": -1,
}

def load_datasets():
    train_df = pd.read_csv(TRAIN_DATA_PATH)
    test_df = pd.read_csv(TEST_DATA_PATH)
    print(f"Train shape: {train_df.shape}")
    print(f"Test shape: {test_df.shape}")
    return train_df, test_df

def prepare_features(train_df, test_df):
    required_columns = {DATETIME_COLUMN, TARGET_COLUMN}

    for dataset_name, dataset in [
        ("train", train_df),
        ("test", test_df),
    ]:
        missing_columns = required_columns - set(dataset.columns)

        if missing_columns:
            raise ValueError(
                f"{dataset_name} dataset is missing columns: "
                f"{sorted(missing_columns)}"
            )

    feature_columns = [
        column
        for column in train_df.columns
        if column not in {DATETIME_COLUMN, TARGET_COLUMN}
    ]

    X_train = train_df[feature_columns]
    y_train = train_df[TARGET_COLUMN]

    X_test = test_df[feature_columns]
    y_test = test_df[TARGET_COLUMN]

    if X_train.isna().any().any():
        raise ValueError("Training features contain missing values")

    if X_test.isna().any().any():
        raise ValueError("Testing features contain missing values")

    return X_train, X_test, y_train, y_test, feature_columns

def train_model(X_train, y_train):
    model = RandomForestRegressor(**MODEL_PARAMS)
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    mse = mean_squared_error(y_test, predictions)
    rmse = mse**0.5
    r2 = r2_score(y_test, predictions)

    metrics = {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
    }
    return metrics

def save_model(model, feature_columns):
    MODEL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    model_artifact = {
        "model": model,
        "features": feature_columns,
        "target": TARGET_COLUMN,
        "prediction_horizon_hours": 3,
    }
    joblib.dump(model_artifact, MODEL_OUTPUT_PATH)
    print(f"Model saved to: {MODEL_OUTPUT_PATH}")

def save_metrics(metrics):
    METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=4)
    print(f"Metrics saved to: {METRICS_OUTPUT_PATH}")

def log_to_mlflow(metrics):
    experiment_name = "weather-temperature-forecast"
    artifact_location = "mlruns/weather-temperature-forecast"
    mlflow.set_tracking_uri("sqlite:///mlflow.db")

    client = MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        experiment_id = client.create_experiment(
            name=experiment_name,
            artifact_location=artifact_location,
        )
    else:
        experiment_id = experiment.experiment_id

    with mlflow.start_run(experiment_id=experiment_id):
        mlflow.log_params(MODEL_PARAMS)
        mlflow.log_metrics(metrics)
        mlflow.log_param("prediction_horizon_hours", 3)
        mlflow.log_param("target_column", TARGET_COLUMN)
        mlflow.log_artifact(str(MODEL_OUTPUT_PATH))
        mlflow.log_artifact(str(METRICS_OUTPUT_PATH))

    print("Experiment logged to MLflow")

def main():
    train_df, test_df = load_datasets()

    X_train, X_test, y_train, y_test, feature_columns = (
        prepare_features(train_df, test_df)
    )

    print(f"Number of model features: {len(feature_columns)}")

    model = train_model(X_train, y_train)
    metrics = evaluate_model(model, X_test, y_test)

    print("Test metrics:")
    print(f"MAE:  {metrics['mae']:.4f}")
    print(f"RMSE: {metrics['rmse']:.4f}")
    print(f"R2:   {metrics['r2']:.4f}")

    save_model(model, feature_columns)
    save_metrics(metrics)
    log_to_mlflow(metrics)


if __name__ == "__main__":
    main()