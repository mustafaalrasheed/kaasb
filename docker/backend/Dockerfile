FROM python:3.12-slim-bookworm AS base

WORKDIR /app

# System deps — curl for health checks, libmagic for file type detection
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Python deps in a separate cached layer
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# Development target — hot reload via mounted volume
# ============================================================
FROM base AS development
COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================
# Production target — non-root user, gunicorn with config file
# ============================================================
FROM base AS production

# Non-root user
RUN groupadd -r kaasb && useradd -r -g kaasb -d /app -s /sbin/nologin kaasb

COPY backend/ .
COPY docker/backend/gunicorn.conf.py /gunicorn.conf.py

# Upload dir owned by app user
RUN mkdir -p /app/uploads && chown -R kaasb:kaasb /app /gunicorn.conf.py

USER kaasb
EXPOSE 8000

# Health check — uses the /health endpoint we fixed to return 503 on degraded
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Gunicorn reads config from /gunicorn.conf.py
CMD ["gunicorn", "app.main:app", "--config", "/gunicorn.conf.py"]
