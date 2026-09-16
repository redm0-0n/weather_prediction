FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY code/deployment/app/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY code/deployment/app/app.py /app/app.py

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--browser.gatherUsageStats", "false"]