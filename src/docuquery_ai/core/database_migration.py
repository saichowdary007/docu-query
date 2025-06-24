import glob
import os
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from docuquery_ai.core.config import settings
from docuquery_ai.core.database import SessionLocal
from docuquery_ai.models.db_models import File, User
from docuquery_ai.services.file_service import create_file_record


def migrate_existing_files():
    """Migrates existing files from the old filesystem-only structure to the new database structure."""
    db = SessionLocal()
    try:
        # Get the first admin user to assign files to if no owner can be determined
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            # Get any user if no admin exists
            admin_user = db.query(User).first()
            if not admin_user:
                print("No users found in the database. Cannot migrate files.")
                return

        # Scan main temp_uploads directory
        scan_directory(settings.TEMP_UPLOAD_FOLDER, admin_user.id, db)

        # Scan user-specific directories if they exist
        users_dirs = glob.glob(os.path.join(settings.TEMP_UPLOAD_FOLDER, "*"))
        for user_dir in users_dirs:
            if os.path.isdir(user_dir):
                user_id = os.path.basename(user_dir)
                # Check if this is a valid user ID
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    scan_directory(user_dir, user.id, db)
                else:
                    # If not a valid user ID, files belong to admin
                    scan_directory(user_dir, admin_user.id, db)

        db.commit()
        print(f"File migration completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during file migration: {str(e)}")
    finally:
        db.close()


def scan_directory(directory: str, user_id: str, db: Session):
    """Scan a directory and create file records for files that don't have DB entries."""
    if not os.path.exists(directory):
        return

    files = glob.glob(os.path.join(directory, "*"))
    for file_path in files:
        if os.path.isfile(file_path):
            filename = os.path.basename(file_path)

            # Check if file record already exists
            existing = (
                db.query(File)
                .filter(File.filename == filename, File.user_id == user_id)
                .first()
            )

            if not existing:
                # Determine file type and structured status
                _, ext = os.path.splitext(filename.lower())
                file_type = ext[1:] if ext else "unknown"
                is_structured = ext in [".csv", ".xls", ".xlsx"]
                structure_type = None

                if is_structured:
                    structure_type = "excel" if ext in [".xls", ".xlsx"] else "csv"

                # Create file record
                create_file_record(
                    db=db,
                    filename=filename,
                    file_path=file_path,
                    file_type=file_type,
                    user_id=user_id,
                    is_structured=is_structured,
                    structure_type=structure_type,
                )
                print(f"Migrated file: {filename} for user {user_id}")
            else:
                print(f"File already has a record: {filename} for user {user_id}")


def run_migrations():
    """Run all database migrations."""
    print("Starting database migrations...")
    migrate_existing_files()
    print("Migrations complete.")
