FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies with explicit sentence-transformers installation
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir sentence-transformers==2.2.2 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories and ensure they're empty
RUN mkdir -p uploads
RUN mkdir -p chroma_db
RUN rm -rf chroma_db/* || true

# Create .env file if it doesn't exist
RUN touch .env

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CHROMA_DB_PATH=/app/chroma_db

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 