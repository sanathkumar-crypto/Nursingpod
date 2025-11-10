# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install system dependencies
# Use host network mode works around DNS issues
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY app_fastapi.py .
COPY bigquery_connector.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Cloud Run uses PORT env var, default to 8080)
EXPOSE 8080

# Use uvicorn for FastAPI production server
CMD exec uvicorn app_fastapi:app --host 0.0.0.0 --port $PORT --workers 2 --timeout-keep-alive 120 --access-log --log-level info


