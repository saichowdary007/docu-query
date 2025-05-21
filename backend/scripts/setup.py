#!/usr/bin/env python3
"""
DocuQuery-AI setup script.
This script initializes the database, creates default admin user,
and sets up the file system for the application.
"""

import os
import sys
import uuid
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, init_db
from app.core.database_migration import run_migrations
from app.models.db_models import User
from app.core.security import get_password_hash
from app.models.user import UserRole
from app.core.config import settings

def setup_database():
    """Initialize database tables and indexes."""
    print("Initializing database...")
    init_db()
    print("Database initialized successfully.")

def create_admin_user():
    """Create a default admin user if no users exist."""
    db = SessionLocal()
    try:
        # Check if any users exist
        user_count = db.query(User).count()
        if user_count == 0:
            admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
            admin_email = os.getenv("ADMIN_EMAIL", "admin@docuquery.ai")
            
            # Create admin user
            admin_user = User(
                id=str(uuid.uuid4()),
                email=admin_email,
                full_name="Admin User",
                hashed_password=get_password_hash(admin_password),
                is_active=True,
                role=UserRole.ADMIN
            )
            
            db.add(admin_user)
            db.commit()
            print(f"Created admin user: {admin_email}")
            print(f"Default password: {admin_password}")
            print("IMPORTANT: Please change the default password immediately!")
        else:
            print(f"Users already exist ({user_count} found). Skipping admin creation.")
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {str(e)}")
    finally:
        db.close()

def setup_file_system():
    """Set up the file system directories."""
    print("Setting up file system...")
    
    # Create main upload directory
    os.makedirs(settings.TEMP_UPLOAD_FOLDER, exist_ok=True)
    
    # Create vector store directory
    vector_db_path = os.path.join("vector_db_data", "faiss_index")
    os.makedirs(vector_db_path, exist_ok=True)
    
    print("File system setup completed.")

def run_migrations_setup():
    """Run database migrations for existing data."""
    print("Running data migrations...")
    run_migrations()
    print("Migrations completed.")

def main():
    """Main setup function."""
    print("====================================")
    print("DocuQuery-AI Setup")
    print("====================================")
    
    setup_database()
    create_admin_user()
    setup_file_system()
    run_migrations_setup()
    
    print("====================================")
    print("Setup completed successfully!")
    print("====================================")

if __name__ == "__main__":
    main() 