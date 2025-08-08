# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies only if needed by wheels fallback
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (leverage Docker layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# Copy project
COPY . /app

# Default environment values (can be overridden by compose)
ENV REDIS_URL=redis://redis:6379 \
    LOGGER=true

# Run the bot
CMD ["python", "rovmarket_bot/main.py"]


