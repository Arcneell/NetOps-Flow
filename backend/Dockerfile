# =============================================================================
# NetOps-Flow Backend Dockerfile - Multi-stage optimized build
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and build
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# Labels
LABEL maintainer="NetOps-Flow Team"
LABEL description="NetOps-Flow Backend API"
LABEL version="2.0.0"

# Create non-root user for security
RUN groupadd -r netops && useradd -r -g netops netops

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    nmap \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy wheels from builder and install
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY backend/ /app/backend/
COPY worker/ /app/worker/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

# Create scripts storage directory
RUN mkdir -p /scripts_storage && chown netops:netops /scripts_storage

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Switch to non-root user
USER netops

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]

# -----------------------------------------------------------------------------
# Stage 3: Development - With hot reload and dev tools
# -----------------------------------------------------------------------------
FROM runtime AS development

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    httpx \
    black \
    isort \
    mypy

# Install PowerShell for dev/testing (AMD64 only - not available on ARM64/Apple Silicon)
RUN arch=$(dpkg --print-architecture) && \
    if [ "$arch" = "amd64" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            wget \
            gnupg \
            software-properties-common \
        && wget -q "https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb" \
        && dpkg -i packages-microsoft-prod.deb \
        && rm packages-microsoft-prod.deb \
        && apt-get update \
        && apt-get install -y powershell \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean; \
    else \
        echo "Skipping PowerShell installation on $arch (not available)"; \
    fi

USER netops

# Override command for development
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
