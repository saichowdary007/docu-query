"""Core functionality for DocuQuery AI."""

from .config import Settings, settings

try:  # Optional database support
    from .database import SessionLocal, get_db, init_db
except Exception:  # pragma: no cover - when SQLAlchemy is missing
    SessionLocal = None
    def get_db():
        raise RuntimeError("Database functionality is unavailable")
    def init_db():
        raise RuntimeError("Database functionality is unavailable")
try:
    from .security import create_access_token, get_password_hash, verify_password
except Exception:  # pragma: no cover - fastapi dependency missing
    def create_access_token(*args, **kwargs):
        raise RuntimeError("Security functionality is unavailable")

    def get_password_hash(password: str) -> str:
        raise RuntimeError("Security functionality is unavailable")

    def verify_password(*args, **kwargs) -> bool:
        raise RuntimeError("Security functionality is unavailable")

__all__ = [
    "Settings",
    "settings",
    "init_db",
    "get_db",
    "SessionLocal",
    "get_password_hash",
    "verify_password",
    "create_access_token",
]
