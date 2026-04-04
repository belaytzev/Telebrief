# Use Python 3.14 slim image — pinned for reproducibility
FROM python:3.14.3-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -r -s /usr/sbin/nologin telebrief

# Create necessary directories and set ownership
RUN mkdir -p logs sessions data && chown -R telebrief:telebrief logs sessions data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('logs/telebrief.log') else 1)"

# Switch to non-root user
USER telebrief

# Run the application
CMD ["python", "main.py"]
