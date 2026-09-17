# Weather prediction MLOps project

This project predicts the temperature in Innopolis three hours ahead. It was made as the first PMLDL assignment and contains a complete pipeline from data collection to deployment.

## Idea

The model uses weather data from Innopolis and four nearby cities: Kazan, Cheboksary, Ulyanovsk and Yoshkar-Ola. For each city it uses temperature, humidity, pressure, wind, precipitation and cloud cover.

Historical data is downloaded from the Open-Meteo Historical Weather API. The Streamlit application uses the Open-Meteo Forecast API to get current weather. Open-Meteo is free and does not require an API key.

The prediction target is the temperature in Innopolis three hours after the input timestamp.

## Tools

- DVC describes the data processing and training pipeline.
- MLflow logs model parameters, metrics and artifacts.
- scikit-learn is used to train a Random Forest model.
- FastAPI provides the prediction API.
- Streamlit provides the web interface.
- Docker runs the API and application in separate containers.
- Airflow starts the full pipeline every five minutes.

## Pipeline

```text
Open-Meteo
    |
    v
collect_history
    |
    v
prepare train/test data
    |
    v
train and evaluate model
    |
    v
FastAPI + Streamlit
```

The DVC stages are defined in `dvc.yaml`:

```text
collect_history -> prepare -> train
```

Data preparation includes missing-value removal, validation of weather values, outlier removal, time features and a chronological 80/20 train-test split.

The model is a `RandomForestRegressor`. Current test results:

```text
MAE:  1.0440 °C
RMSE: 1.3864 °C
R²:   0.9196
```

## Project structure

```text
code/datasets             data collection and preparation
code/models               model training
code/deployment/api       FastAPI service
code/deployment/app       Streamlit application
data/raw                  raw data
data/processed            train and test data
models                    trained model
metrics                   test metrics
services/airflow          Airflow DAG and Docker configuration
dvc.yaml                  DVC pipeline
```

## Local setup

Requirements:

- Python 3.12
- Docker Desktop
- Docker Compose

Clone the repository:

```bash
git clone https://github.com/redm0-0n/weather_prediction.git
cd weather_prediction
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the data and model pipeline

```powershell
dvc repro
dvc dag
dvc metrics show
```

Generated data and the model are not stored directly in Git. They can be recreated from Open-Meteo by running `dvc repro`.

## MLflow

Training creates the `weather-temperature-forecast` experiment. Start the UI with:

```powershell
mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000`.

## Docker deployment

The model must exist before building the API image:

```powershell
dvc repro
docker compose -f code/deployment/docker-compose.yml up --build -d
```

Services:

- Streamlit: `http://localhost:8501`
- FastAPI docs: `http://localhost:8000/docs`
- FastAPI health check: `http://localhost:8000/health`

Stop the containers:

```powershell
docker compose -f code/deployment/docker-compose.yml down
```

## Airflow automation

Airflow runs these tasks:

```text
run_dvc_pipeline -> deploy_application -> verify_services
```

The DAG schedule is `*/5 * * * *`.

Start Airflow:

```powershell
docker compose -f services/airflow/docker-compose.yml up --build -d
docker logs weather-airflow --tail 100
```

Open `http://localhost:8080`, enable `weather_mlops_pipeline` and use `Single Run` for the first check. Later runs start automatically according to the schedule.

The running application consists of three containers:

```text
weather-airflow
weather-api
weather-app
```
