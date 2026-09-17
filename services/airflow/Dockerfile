FROM apache/airflow:3.1.7-python3.12

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==3.1.7" \
    -r /tmp/requirements.txt