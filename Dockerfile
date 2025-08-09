FROM python:3.11.10-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONFAULTHANDLER=1

WORKDIR /app

# Install Python dependencies first (leverage Docker layer caching)
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --only-binary=:all: -r /app/requirements.txt || \
       python -m pip install -r /app/requirements.txt

# Copy project
COPY . /app

# Create non-root user and adjust ownership
RUN useradd -m -u 10001 appuser \
    && chown -R appuser:appuser /app

# Default environment values (can be overridden by compose)
ENV REDIS_URL=redis://redis:6379 \
    LOGGER=true

USER appuser

# Run the bot
CMD ["python", "rovmarket_bot/main.py"]


