FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    # Additional dependencies for Excel processing
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies with optimized caching
RUN pip install --no-cache-dir -U pip && \
    # Install spaCy first with language model
    pip install --no-cache-dir spacy==3.7.2 && \
    python -m spacy download en_core_web_sm && \
    # Install sentence transformers explicitly
    pip install --no-cache-dir sentence-transformers==2.2.2 && \
    # Install Excel-related packages explicitly
    pip install --no-cache-dir xlrd==2.0.1 openpyxl==3.1.2 pyxlsb==1.0.10 && \
    # Install remaining dependencies
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