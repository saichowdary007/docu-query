from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLAlchemyEnum
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.models.user import UserRole


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