# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (use requirements.txt only - NOT recruitment.docker.txt which is documentation)
COPY requirements.txt .

# Create wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt
RUN pip install --no-cache-dir --prefix=/install /build/wheels/*

# Stage 2: Frontend build stage
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /frontend

COPY package.json package-lock.json ./
RUN npm ci

COPY vite.config.js ./
COPY detail_project/static/detail_project ./detail_project/static/detail_project

RUN npm run build

# Stage 3: Runtime stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install runtime dependencies
# F6 (launch audit): git removed — nothing in the app shells out to git at
# runtime; it only added image bloat and attack surface.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python dependencies from the builder.
COPY --from=builder /install /usr/local

# Copy project
COPY . .

# Copy compiled frontend assets only; Node/npm stay in the build stage.
COPY --from=frontend-builder \
    /frontend/detail_project/static/detail_project/dist \
    /app/detail_project/static/detail_project/dist

# Create necessary directories
RUN mkdir -p /app/logs /app/staticfiles /app/media /app/coverage

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Create app user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Ensure entrypoint is executable
RUN chmod +x /app/docker-entrypoint.sh

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f \
        -H "Host: healthcheck.local" \
        -H "X-Forwarded-Proto: https" \
        http://127.0.0.1:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Run entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
