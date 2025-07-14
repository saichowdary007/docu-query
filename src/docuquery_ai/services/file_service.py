import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from docuquery_ai.core.config import settings
from docuquery_ai.models.db_models import File, User


def create_file_record(
    db: Session,
    filename: str,
    file_path: str,
    file_type: str,
    user_id: str,
    is_structured: bool = False,
    structure_type: Optional[str] = None,
) -> File:
    """Create a file record in the database."""
    file_record = File(
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        is_structured=is_structured,
        structure_type=structure_type,
        user_id=user_id,
    )

    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record


def get_user_files(db: Session, user_id: str) -> List[File]:
    """Get all files for a specific user."""
    return db.query(File).filter(File.user_id == user_id).all()


def get_file_by_filename(db: Session, filename: str, user_id: str) -> Optional[File]:
    """Get a file by its filename and user_id."""
    return (
        db.query(File)
        .filter(File.filename == filename, File.user_id == user_id)
        .first()
    )


def delete_file_record(db: Session, file_id: str) -> bool:
    """Delete a file record from the database."""
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        return False

    db.delete(file)
    db.commit()
    return True


def file_record_to_dict(file: File) -> Dict[str, Any]:
    """Convert a File model to a dictionary for API responses."""
    return {
        "filename": file.filename,
        "type": file.file_type,
        "is_structured": file.is_structured,
        "structure_type": file.structure_type,
        "created_at": file.created_at.isoformat() if file.created_at else None,
    }


def ensure_user_upload_dir(user_id: str) -> str:
    """Ensure user upload directory exists and return the path."""
    user_upload_dir = os.path.join(settings.TEMP_UPLOAD_FOLDER, user_id)
    os.makedirs(user_upload_dir, exist_ok=True)
    return user_upload_dir


def save_uploaded_file(file_content, target_path: str) -> bool:
    """Save uploaded file content to target path."""
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file_content, buffer)
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False


def delete_file(file_path: str) -> bool:
    """Delete a file from the filesystem."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return True
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False
