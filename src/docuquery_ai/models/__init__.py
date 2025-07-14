"""Data models for DocuQuery AI."""

try:  # Optional SQLAlchemy models
    from .db_models import File, User
except Exception:  # pragma: no cover - allow import without SQLAlchemy
    File = User = None
from .pydantic_models import FileProcessRequest, QueryRequest, QueryResponse
from .user import TokenPayload, UserCreate, UserResponse, UserRole

__all__ = [
    "User",
    "File",
    "QueryRequest",
    "QueryResponse",
    "FileProcessRequest",
    "UserCreate",
    "UserResponse",
    "UserRole",
    "TokenPayload",
]
