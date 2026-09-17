# Weather MLOps Pipeline

An end-to-end MLOps project that predicts the temperature in Innopolis three hours ahead. The repository implements data collection and processing, model training and evaluation, experiment tracking, an inference API, a web application, containerized deployment, and scheduled automation.

## Project idea

The model uses the current weather in Innopolis and four nearby cities:

- Kazan;
- Cheboksary;
- Ulyanovsk;
- Yoshkar-Ola.

Nearby cities provide additional information about regional weather conditions. For every timestamp, the model receives temperature, humidity, atmospheric pressure, wind speed, wind direction, precipitation, and cloud cover for all five cities. It predicts the temperature in Innopolis three hours later.

The web application retrieves current weather automatically, displays it in an editable table, sends the resulting features to the model API, and displays the prediction.

## Data sources

The project uses the free [Open-Meteo](https://open-meteo.com/) API and does not require an API key.

Two Open-Meteo endpoints are used:

- Historical Weather API (`archive-api.open-meteo.com`) provides one year of hourly observations for model training and testing. The archive has a publication delay, so the data collection script requests data up to five days before the current date.
- Forecast API (`api.open-meteo.com`) provides current model-based weather conditions for the Streamlit application.

The following variables are collected:

- temperature at 2 metres;
- relative humidity at 2 metres;
- mean sea-level pressure;
- wind speed at 10 metres;
- wind direction at 10 metres;
- precipitation;
- total cloud cover.

## Pipeline architecture

```text
Open-Meteo Historical API
            |
            v
data/raw/weather_history.csv
            |
            v
Data cleaning, outlier handling and chronological split
            |
            v
data/processed/train.csv + data/processed/test.csv
            |
            v
RandomForestRegressor + MLflow
            |
            v
models/model.pkl + metrics/metrics.json
            |
            v
FastAPI container <--- Streamlit container
            ^                   |
            |                   v
            +------------ prediction

Airflow triggers the complete DVC and deployment pipeline every 5 minutes.
```

## Technology stack

| Tool | Application in the project |
|---|---|
| Python | Data collection, preprocessing, training, API, application, and deployment scripts |
| pandas | Data loading, cleaning, pivoting, feature creation, and splitting |
| scikit-learn | Random Forest training and model evaluation |
| DVC | Definition and reproducible execution of the data and model pipeline |
| MLflow | Logging model parameters, metrics, and model artifacts |
| FastAPI | Model inference API |
| Streamlit | Interactive web application with editable input data |
| Docker | Separate images and containers for the API and application |
| Docker Compose | Local deployment of the API and application |
| Apache Airflow | Automatic pipeline execution every five minutes |
| Open-Meteo | Historical and current weather data |

## Pipeline stages

### 1. Data engineering

The `collect_history` DVC stage downloads hourly historical weather data for five cities and saves it to:

```text
data/raw/weather_history.csv
```

The `prepare` stage:

- parses timestamps;
- transforms city observations into one row per timestamp;
- removes missing and infinite values;
- removes physically invalid measurements;
- detects extreme temperature, pressure, and wind-speed values using a relaxed IQR rule;
- creates hour, weekday, and month features;
- creates the target by shifting Innopolis temperature by three hours;
- performs a chronological 80/20 train-test split.

Outputs:

```text
data/processed/train.csv
data/processed/test.csv
```

### 2. Model engineering

The `train` DVC stage trains a `RandomForestRegressor` using 38 features. The trained model is packaged together with its feature order and target metadata:

```text
models/model.pkl
```

The following test metrics are calculated and logged to DVC and MLflow:

| Metric | Current value |
|---|---:|
| MAE | 1.0440 °C |
| RMSE | 1.3864 °C |
| R² | 0.9196 |

Machine-readable metrics are stored in:

```text
metrics/metrics.json
```

### 3. Deployment

FastAPI loads the packaged model and provides:

- `GET /health` — service health and model status;
- `GET /model-info` — target and required feature names;
- `POST /predict` — temperature prediction.

Streamlit loads current weather from Open-Meteo into an editable table. Pressing the prediction button sends all model features to FastAPI and displays the predicted temperature.

The API and Streamlit application run in separate Docker containers.

## Repository structure

```text
weather_prediction/
├── code/
│   ├── datasets/
│   │   ├── collect_history.py
│   │   └── prepare_dataset.py
│   ├── models/
│   │   └── train.py
│   └── deployment/
│       ├── api/
│       │   ├── main.py
│       │   ├── requirements.txt
│       │   └── Dockerfile
│       ├── app/
│       │   ├── app.py
│       │   ├── requirements.txt
│       │   └── Dockerfile
│       ├── deploy.py
│       └── docker-compose.yml
├── data/
│   ├── raw/
│   └── processed/
├── metrics/
│   └── metrics.json
├── models/
├── notebooks/
├── services/
│   └── airflow/
│       ├── dags/
│       │   └── weather_pipeline.py
│       ├── Dockerfile
│       ├── requirements.txt
│       └── docker-compose.yml
├── dvc.yaml
├── dvc.lock
└── requirements.txt
```

## Prerequisites

- Python 3.12;
- Git;
- Docker Desktop with Docker Compose;
- at least 4 GB of memory available to Docker.

Airflow is run in Docker and does not need to be installed directly on Windows.

## Local installation

Clone the repository and enter it:

```bash
git clone https://github.com/redm0-0n/weather_prediction.git
cd weather_prediction
```

Create a virtual environment:

```bash
python -m venv .venv
```

PowerShell activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running the DVC pipeline

Run all data and model stages:

```bash
dvc repro
```

Display the pipeline graph and metrics:

```bash
dvc dag
dvc metrics show
dvc status
```

The raw data, processed datasets, and model are generated by the pipeline and are intentionally not stored directly in Git. No DVC remote is required because the source data can be downloaded again from Open-Meteo.

## Running MLflow

Training writes experiments to the local SQLite database `mlflow.db`. Start the UI from the repository root:

```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Open:

```text
http://127.0.0.1:5000
```

The experiment name is `weather-temperature-forecast`.

## Running API and application with Docker Compose

Generate the model before building the API image:

```bash
dvc repro
```

Build and start the two deployment containers:

```bash
docker compose -f code/deployment/docker-compose.yml up --build -d
```

Available services:

| Service | URL |
|---|---|
| Streamlit application | `http://localhost:8501` |
| FastAPI documentation | `http://localhost:8000/docs` |
| FastAPI health endpoint | `http://localhost:8000/health` |

Check container status:

```bash
docker compose -f code/deployment/docker-compose.yml ps
```

Stop the services:

```bash
docker compose -f code/deployment/docker-compose.yml down
```

## Running the automated Airflow pipeline

The Airflow DAG has the following task graph:

```text
run_dvc_pipeline
        |
        v
deploy_application
        |
        v
verify_services
```

Its schedule is:

```text
*/5 * * * *
```

Before starting Airflow, stop deployment containers launched through Docker Compose:

```bash
docker compose -f code/deployment/docker-compose.yml down
```

Build and start Airflow:

```bash
docker compose -f services/airflow/docker-compose.yml up --build -d
```

Read the standalone administrator credentials:

```bash
docker logs weather-airflow --tail 100
```

Open the Airflow UI:

```text
http://localhost:8080
```

Enable `weather_mlops_pipeline` and use **Single Run** for the first manual test. Subsequent runs are scheduled automatically every five minutes. `max_active_runs=1` prevents concurrent pipeline runs.

The deployment task builds new API and application images, replaces the previous containers, waits for the API health check, and starts Streamlit. The Docker socket is mounted into the Airflow container for this local educational workflow.

Check all running containers:

```bash
docker ps
```

Expected containers:

```text
weather-airflow
weather-api
weather-app
```

Stop Airflow and the automated services:

```bash
docker compose -f services/airflow/docker-compose.yml down
docker rm -f weather-api weather-app
```

## Reproducing a prediction

1. Run the DVC pipeline to generate `models/model.pkl`.
2. Start the API and application containers.
3. Open Streamlit at `http://localhost:8501`.
4. Review or edit the automatically loaded current weather values.
5. Press **Predict temperature in 3 hours**.
6. The application sends the request to FastAPI and displays the returned prediction.

## Notes

- The model file is larger than GitHub's regular file limit and is regenerated by `dvc repro`.
- Generated data, DVC cache, MLflow database, experiment artifacts, and Airflow logs are excluded from Git.
- The Airflow Docker configuration is intended for a local course demonstration, not a production environment.
