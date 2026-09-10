FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
COPY pyproject.toml .

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config ./config
COPY sql ./sql

RUN python -m pip install --no-cache-dir .

CMD ["python", "-m", "scientific_pipeline.validate", "--help"]
