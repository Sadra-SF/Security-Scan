# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    netcat-openbsd \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
ARG APP_USER=appuser
ARG APP_UID=10001
RUN useradd -m -u ${APP_UID} -s /bin/bash ${APP_USER}

WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

# Copy source
COPY . /app

# Ensure ownership
RUN chown -R ${APP_USER}:${APP_USER} /app

USER ${APP_USER}

# Default command is overridden per service in docker-compose
CMD ["bash", "-lc", "python backend/src/manage.py runserver 0.0.0.0:8000"]