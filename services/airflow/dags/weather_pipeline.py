from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

PROJECT_ROOT = "/opt/project"

with DAG(
    dag_id="weather_mlops_pipeline",
    description="Weather MLOps pipeline with DVC and Docker",
    schedule="*/5 * * * *",
    start_date=pendulum.datetime(
        2026,
        1,
        1,
        tz="Europe/Moscow",
    ),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "weather-mlops",
        "retries": 1,
        "retry_delay": timedelta(minutes=1),
    },
    tags=["mlops", "dvc", "weather", "deployment"],
) as dag:
    run_dvc_pipeline = BashOperator(
        task_id="run_dvc_pipeline",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "dvc repro --force"
        ),
        execution_timeout=timedelta(minutes=20),
    )

    deploy_application = BashOperator(
        task_id="deploy_application",
        bash_command=(
            f"cd {PROJECT_ROOT} && "
            "python code/deployment/deploy.py"
        ),
        execution_timeout=timedelta(minutes=20),
    )

    verify_services = BashOperator(
        task_id="verify_services",
        bash_command=(
            "python -c \""
            "import urllib.request; "
            "urllib.request.urlopen("
            "'http://host.docker.internal:8000/health'"
            "); "
            "urllib.request.urlopen("
            "'http://host.docker.internal:8501'"
            ")"
            "\""
        ),
        execution_timeout=timedelta(minutes=2),
    )

    run_dvc_pipeline >> deploy_application >> verify_services