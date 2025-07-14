"""Services for DocuQuery AI."""

try:
    from .file_service import create_file_record
except Exception:  # pragma: no cover - optional SQLAlchemy dependency missing
    def create_file_record(*args, **kwargs):
        raise RuntimeError("Database functionality is unavailable")

__all__ = [
    "create_file_record",
]