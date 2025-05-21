#!/usr/bin/env python3
"""
DocuQuery-AI backend run script.
This script initializes the database and starts the FastAPI server.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent))

# Import after path setup
from scripts.setup import setup_database, setup_file_system, create_admin_user

def initialize():
    """Initialize required components before starting the server."""
    # Create required directories and initialize database
    setup_file_system()
    setup_database()
    create_admin_user()

def main():
    """Start the FastAPI server."""
    # Get environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    # Initialize required components
    initialize()
    
    # Start the server
    print(f"Starting DocuQuery-AI backend on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload
    )

if __name__ == "__main__":
    main() 