"""
DocuQuery AI - A powerful document query system using RAG and LLM technologies.

This package provides document processing, vector storage, and natural language querying
capabilities for PDF, DOCX, PPTX, TXT, MD, CSV, XLS, and XLSX files.
"""

__version__ = "0.1.0"
__author__ = "DocuQuery AI Team"
__email__ = "contact@docuquery-ai.com"

from .client import DocumentQueryClient
from .core.config import Settings
from .models.pydantic_models import FileProcessRequest, QueryRequest, QueryResponse
from .models.user import UserCreate, UserResponse

__all__ = [
    "DocumentQueryClient",
    "Settings",
    "QueryRequest",
    "QueryResponse",
    "FileProcessRequest",
    "UserCreate",
    "UserResponse",
]
