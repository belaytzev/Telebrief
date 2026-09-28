# Use Python 3.14 slim image — pinned for reproducibility
FROM mirror.gcr.io/library/python:3.14.3-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install exactly the versions in uv.lock; the app itself runs from source
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_NO_CACHE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Create non-root user
RUN useradd -r -u 1000 -s /usr/sbin/nologin telebrief

# Create necessary directories and set ownership
RUN mkdir -p logs sessions data && chown -R telebrief:telebrief logs sessions data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os, signal; os.kill(1, 0)"

# Switch to non-root user
USER telebrief

# Run the application
CMD ["python", "main.py"]
