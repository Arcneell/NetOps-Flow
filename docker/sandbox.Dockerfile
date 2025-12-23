# =============================================================================
# NetOps-Flow Sandbox Dockerfile
# Secure, minimal container for script execution
# =============================================================================

FROM python:3.11-slim

# Labels
LABEL maintainer="NetOps-Flow Team"
LABEL description="NetOps-Flow Script Sandbox"
LABEL version="1.0.0"

# Install minimal dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with minimal permissions
RUN groupadd -r sandbox && useradd -r -g sandbox -s /bin/bash sandbox

# Create workspace directory
RUN mkdir -p /workspace && chown sandbox:sandbox /workspace

# Set restrictive permissions
RUN chmod 755 /workspace

# No network access by default (configured in docker run)
# Read-only filesystem (configured in docker run)
# Dropped capabilities (configured in docker run)

# Switch to non-root user
USER sandbox
WORKDIR /workspace

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["/bin/bash"]
