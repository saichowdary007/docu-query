"""
Main client interface for DocuQuery AI package.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core.config import Settings
from .models.pydantic_models import QueryRequest, QueryResponse

from .db.manager import MultiDatabaseManager

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

        # Initialize database, vector store, and knowledge graph
        self.db_manager = MultiDatabaseManager()

        self._initialized = True

    def dispose(self):
        """
        Disposes of resources held by the client, such as database connections.
        """
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.dispose()

    def _validate_credentials(self):
        """
        Validate that required credentials are set for production use.
        """
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

    async def upload_document(self, file_path: str, user_id: str) -> Dict[str, Any]:
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
        
        await self.db_manager.ingest_document(str(source_path), filename)

        return {
            "success": True,
            "filename": filename,
        }

    async def query(
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

        from .rag.processor import RAGProcessor
        rag_processor = RAGProcessor(self.db_manager)
        answer = await rag_processor.process(question)
        return QueryResponse(answer=answer, sources="", type="text")

    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all uploaded documents for a user.
        (Currently returns a placeholder empty list as direct DB interaction is removed from client)

        Args:
            user_id: User identifier

        Returns:
            List of document information dictionaries
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        # Placeholder: In a real scenario, this would query the relational database
        # via MultiDatabaseManager to list documents associated with the user.
        return []

    async def delete_document(self, file_id: str, user_id: str) -> bool:
        """
        Delete a document's database record, its vectors, and the physical file.
        (Currently returns True as a placeholder, direct DB interaction is removed from client)

        Args:
            file_id: File identifier
            user_id: User identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._initialized:
            raise RuntimeError("Client not initialized")

        # Placeholder: In a real scenario, this would interact with MultiDatabaseManager
        # to delete the document from all relevant databases and storage.
        return True