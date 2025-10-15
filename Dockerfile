FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INSIGHTFACE_HOME=/usr/local/.insightface \
    HF_HOME=/usr/local/.cache/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-railway.txt requirements-railway.txt
RUN pip install --no-cache-dir -r requirements-railway.txt
COPY . .

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0"]
