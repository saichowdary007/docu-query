import uuid

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.sql import func

from docuquery_ai.core.database import Base
from docuquery_ai.models.user import UserRole


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth users
    is_active = Column(Boolean, default=True)
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # OAuth related fields
    google_id = Column(String, unique=True, nullable=True)
    profile_picture = Column(String, nullable=True)

    # Optional refresh token storage
    refresh_token = Column(Text, nullable=True)


class File(Base):
    """Database model for files uploaded by users."""

    __tablename__ = "files"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    is_structured = Column(Boolean, default=False)
    structure_type = Column(String, nullable=True)  # e.g., "excel", "csv"
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
