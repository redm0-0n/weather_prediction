import time
from pathlib import Path
import docker
from docker.errors import NotFound

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_IMAGE = "weather-api:latest"
APP_IMAGE = "weather-app:latest"
API_CONTAINER = "weather-api"
APP_CONTAINER = "weather-app"
NETWORK_NAME = "weather-mlops-network"

def print_build_logs(logs):
    for entry in logs:
        message = entry.get("stream")
        if message:
            print(message.strip())

def build_image(client, image_name, dockerfile):
    print(f"Building {image_name}")
    image, logs = client.images.build(
        path=str(PROJECT_ROOT),
        dockerfile=dockerfile,
        tag=image_name,
        rm=True,
    )
    print_build_logs(logs)
    return image

def remove_container(client, container_name):
    try:
        container = client.containers.get(container_name)
        print(f"Removing existing container: {container_name}")
        container.remove(force=True)
    except NotFound:
        pass

def get_or_create_network(client):
    try:
        return client.networks.get(NETWORK_NAME)
    except NotFound:
        return client.networks.create(
            NETWORK_NAME,
            driver="bridge",
        )

def wait_until_healthy(container, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        container.reload()

        status = container.attrs["State"]["Status"]
        health = (
            container.attrs["State"]
            .get("Health", {})
            .get("Status")
        )

        print(
            f"{container.name}: "
            f"status={status}, health={health}"
        )

        if status == "exited":
            logs = container.logs().decode(
                "utf-8",
                errors="replace",
            )
            raise RuntimeError(
                f"{container.name} exited:\n{logs}"
            )

        if health == "healthy":
            return
        time.sleep(5)

    raise TimeoutError(
        f"{container.name} did not become healthy"
    )

def start_api(client, network):
    healthcheck = {
        "test": [
            "CMD",
            "python",
            "-c",
            (
                "import urllib.request; "
                "urllib.request.urlopen("
                "'http://localhost:8000/health'"
                ")"
            ),
        ],
        "interval": 10_000_000_000,
        "timeout": 5_000_000_000,
        "retries": 5,
        "start_period": 10_000_000_000,
    }

    container = client.containers.run(
        API_IMAGE,
        name=API_CONTAINER,
        detach=True,
        network=network.name,
        ports={"8000/tcp": 8000},
        restart_policy={"Name": "unless-stopped"},
        healthcheck=healthcheck,
    )

    wait_until_healthy(container)

def start_app(client, network):
    client.containers.run(
        APP_IMAGE,
        name=APP_CONTAINER,
        detach=True,
        network=network.name,
        ports={"8501/tcp": 8501},
        environment={
            "API_URL": "http://weather-api:8000",
        },
        restart_policy={"Name": "unless-stopped"},
    )

def main():
    client = docker.from_env()
    client.ping()

    build_image(
        client,
        API_IMAGE,
        "code/deployment/api/Dockerfile",
    )
    build_image(
        client,
        APP_IMAGE,
        "code/deployment/app/Dockerfile",
    )

    remove_container(client, APP_CONTAINER)
    remove_container(client, API_CONTAINER)

    network = get_or_create_network(client)

    start_api(client, network)
    start_app(client, network)

    print("Deployment completed")
    print("FastAPI: http://localhost:8000")
    print("Streamlit: http://localhost:8501")

if __name__ == "__main__":
    main()