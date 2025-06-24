"""
Main client interface for DocuQuery AI package.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core.config import Settings
from .core.database import SessionLocal, get_db, init_db
from .models.pydantic_models import QueryRequest, QueryResponse
from .services.file_parser import get_documents_from_file
from .services.file_service import create_file_record, delete_file, get_file_by_filename
from .services.query_engine import process_query
from .services.vector_store import (
    add_documents_to_store,
    initialize_vector_store,
    remove_documents_by_source,
)


class DocumentQueryClient:
    """
    Main client for DocuQuery AI package.

    Provides a simple interface for document upload and querying.
    """

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        google_project_id: Optional[str] = None,
        vector_store_path: Optional[str] = None,
        temp_upload_folder: Optional[str] = None,
    ):
        """
        Initialize the DocumentQueryClient.

        Args:
            google_api_key: Google API key for Vertex AI
            google_project_id: Google Cloud project ID
            vector_store_path: Path to store vector database
            temp_upload_folder: Path for temporary file uploads
        """
        # Initialize settings
        self.settings = Settings()

        # Override settings if provided
        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
            self.settings.GOOGLE_API_KEY = google_api_key

        if google_project_id:
            os.environ["GOOGLE_PROJECT_ID"] = google_project_id
            self.settings.GOOGLE_PROJECT_ID = google_project_id

        if vector_store_path:
            self.settings.VECTOR_STORE_PATH = vector_store_path

        if temp_upload_folder:
            self.settings.TEMP_UPLOAD_FOLDER = temp_upload_folder

        # Ensure directories exist
        os.makedirs(self.settings.VECTOR_STORE_PATH, exist_ok=True)
        os.makedirs(self.settings.TEMP_UPLOAD_FOLDER, exist_ok=True)

        # Validate environment variables for production use
        self._validate_credentials()

        # Initialize database and vector store
        init_db()
        initialize_vector_store()

        self._initialized = True

    def _validate_credentials(self):
        """Validate that required credentials are set for production use."""
        if (
            self.settings.GOOGLE_API_KEY == "test-api-key"
            or self.settings.GOOGLE_PROJECT_ID == "test-project-id"
        ):
            print(
                "⚠️  Warning: Using test credentials. Set GOOGLE_API_KEY and GOOGLE_PROJECT_ID environment variables for production use."
            )

        if (
            self.settings.API_KEY == "test-security-key"
            or self.settings.JWT_SECRET_KEY == "test-jwt-secret-key"
        ):
            print(
                "⚠️  Warning: Using test security keys. Set API_KEY and JWT_SECRET_KEY environment variables for production use."
            )

    def upload_document(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """
        Upload and process a document.

        Args:
            file_path: Path to the document file
            user_id: User identifier

        Returns:
            Dictionary with upload status and file information
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {source_path}")

        filename = source_path.name

        db = SessionLocal()
        try:
            # Check if this user has already uploaded a file with the same name
            existing_file = get_file_by_filename(db, filename=filename, user_id=user_id)
            if existing_file:
                # If it exists, remove the old one first to ensure a clean update
                remove_documents_by_source(source=existing_file.filename)
                db.delete(existing_file)
                db.commit()

            # Parse file into LangChain Document objects
            documents = get_documents_from_file(str(source_path), filename)

            # Determine if the file is structured based on its extension
            structured_extensions = [".csv", ".xls", ".xlsx"]
            is_structured = source_path.suffix.lower() in structured_extensions
            structure_type = (
                source_path.suffix.lower().replace(".", "") if is_structured else None
            )

            # Create file record in database
            file_record = create_file_record(
                db=db,
                filename=filename,
                file_path=str(source_path),
                file_type=source_path.suffix.lower(),
                user_id=user_id,
                is_structured=is_structured,
                structure_type=structure_type,
            )

            # Add documents to vector store
            if documents:
                add_documents_to_store(documents)

            return {
                "success": True,
                "file_id": file_record.id,
                "filename": file_record.filename,
                "file_type": file_record.file_type,
                "is_structured": file_record.is_structured,
                "documents_count": len(documents),
            }

        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def query(
        self, question: str, user_id: str, file_ids: Optional[List[str]] = None
    ) -> QueryResponse:
        """
        Query the uploaded documents.

        Args:
            question: Natural language question
            user_id: User identifier
            file_ids: Optional list of specific file IDs to query

        Returns:
            QueryResponse with answer and sources
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        query_request = QueryRequest(question=question, file_ids=file_ids or [])

        db = SessionLocal()
        try:
            response = process_query(
                query_request=query_request, user_id=user_id, db=db
            )
            return response
        finally:
            db.close()

    def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all uploaded documents for a user.

        Args:
            user_id: User identifier

        Returns:
            List of document information dictionaries
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        from .models.db_models import File

        db = SessionLocal()
        try:
            files = db.query(File).filter(File.user_id == user_id).all()
            return [
                {
                    "file_id": file.id,
                    "filename": file.filename,
                    "file_type": file.file_type,
                    "is_structured": file.is_structured,
                    "created_at": (
                        file.created_at.isoformat() if file.created_at else None
                    ),
                }
                for file in files
            ]
        finally:
            db.close()

    def delete_document(self, file_id: str, user_id: str) -> bool:
        """
        Delete a document's database record, its vectors, and the physical file.

        Args:
            file_id: File identifier
            user_id: User identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        from .models.db_models import File

        db = SessionLocal()
        try:
            file_record = (
                db.query(File)
                .filter(File.id == file_id, File.user_id == user_id)
                .first()
            )

            if file_record:
                # 1. Remove from vector store
                remove_documents_by_source(file_record.filename)

                # 2. Delete the physical file
                delete_file(file_record.file_path)

                # 3. Delete file record from database
                db.delete(file_record)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error deleting document {file_id}: {e}")
            return False
        finally:
            db.close()
