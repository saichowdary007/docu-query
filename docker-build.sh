#!/bin/bash
set -e

echo "Building and deploying DocuQuery-AI containers..."

# Build and start the containers
docker-compose build --no-cache
docker-compose up -d

echo "DocuQuery-AI is now running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5174"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop containers: docker-compose down" 