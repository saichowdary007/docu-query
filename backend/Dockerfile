FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for Python package builds
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create directories for volumes
RUN mkdir -p /app/vector_db_data /app/temp_uploads

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8000

# Set environment variables for Vertex AI if using ADC with a service account key
# ENV GOOGLE_APPLICATION_CREDENTIALS /app/path/to/your-service-account-key.json 
# Copy the key file if you use this method:
# COPY path/to/your-service-account-key.json /app/path/to/your-service-account-key.json

# Install system dependencies that might be needed by some Python packages (e.g., for certain builds)
# Example: apt-get install -y build-essential libpq-dev
# For Faiss, you might not need extra deps with faiss-cpu. If using Pillow for images later, add libjpeg-dev etc.

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/app

# Create non-root user for security
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/v1/health || exit 1

# Command to run the application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
