FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY code/deployment/api/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY code/deployment/api /app/code/deployment/api
COPY models/model.pkl /app/models/model.pkl

EXPOSE 8000

CMD ["uvicorn", "main:app", "--app-dir", "code/deployment/api", "--host", "0.0.0.0", "--port", "8000"]