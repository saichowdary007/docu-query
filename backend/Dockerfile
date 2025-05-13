FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for Python package builds
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Vertex AI if using ADC with a service account key
# ENV GOOGLE_APPLICATION_CREDENTIALS /app/path/to/your-service-account-key.json 
# Copy the key file if you use this method:
# COPY path/to/your-service-account-key.json /app/path/to/your-service-account-key.json

# Install system dependencies that might be needed by some Python packages (e.g., for certain builds)
# Example: apt-get install -y build-essential libpq-dev
# For Faiss, you might not need extra deps with faiss-cpu. If using Pillow for images later, add libjpeg-dev etc.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
