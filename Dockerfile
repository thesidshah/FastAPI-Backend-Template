# Multi-stage build for production FastAPI application

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata and sources required for packaging
COPY pyproject.toml README.md ./
COPY src ./src

# Install dependencies and the project itself
# Note: Base install includes Phase 1 dependencies
# For production scaling (Phase 4), use: pip install --no-cache-dir ".[scaling]"
RUN pip install --no-cache-dir --upgrade "pip>=25.2" "setuptools>=78.1.1" && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir ".[scaling]"

# Stage 2: Runtime
FROM python:3.11-slim

# Upgrade pip and setuptools to fix security vulnerabilities
RUN pip install --no-cache-dir --upgrade "pip>=25.2" "setuptools>=78.1.1"

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and configuration
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser gunicorn.conf.py ./

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENVIRONMENT=production \
    APP_LOG_FORMAT=json

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health/live', timeout=2)"

# Run application using factory pattern
# The --factory flag tells uvicorn/gunicorn that create_app is a callable that returns a FastAPI instance
#
# Level 1 (Development/Single worker):
#   CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
#
# Level 1 (Multi-worker):
#   CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
#
# Level 2 (Production with Gunicorn - RECOMMENDED):
CMD ["gunicorn", "app.main:create_app", "--factory", "-c", "gunicorn.conf.py"]
