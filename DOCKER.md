# DocuQuery-AI Docker Deployment Guide

This guide explains how to deploy DocuQuery-AI using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git to clone the repository

## Quick Start

1. Clone the repository:
   ```
   git clone <repository-url>
   cd DocuQuery-AI
   ```

2. Build and run using the provided script:
   ```
   ./docker-build.sh
   ```

   Or manually with Docker Compose:
   ```
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. Access the application:
   - Frontend: http://localhost:5174
   - Backend API: http://localhost:8000

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
GOOGLE_API_KEY=your_google_api_key_here
```

The Google API key is optional but recommended for better embedding and compression features.

## Container Information

- **Backend**: Python 3.11 FastAPI application with spaCy NLP
- **Frontend**: Node.js application with Vite and React, served by Nginx

## Data Persistence

The following data is persisted in Docker volumes:
- `docuquery_uploads`: Uploaded documents
- `docuquery_chroma_db`: Vector database

## Troubleshooting

### Viewing Logs

```
docker-compose logs -f
```

To see logs for a specific service:

```
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restarting Services

```
docker-compose restart backend
docker-compose restart frontend
```

### Complete Reset

To remove all containers and volumes (will delete all data):

```
docker-compose down -v
```

## Advanced Configuration

To change ports or other settings, modify the `docker-compose.yml` file. 