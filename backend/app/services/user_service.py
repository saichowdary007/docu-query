from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional
from datetime import datetime

from app.models.db_models import User
from app.models.user import UserCreate, UserResponse, UserRole
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    """Get a user by Google ID."""
    return db.query(User).filter(User.google_id == google_id).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user with email and password."""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=user_data.is_active,
        role=user_data.role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_or_update_google_user(
    db: Session, 
    email: str, 
    google_id: str, 
    name: Optional[str] = None,
    profile_picture: Optional[str] = None
) -> User:
    """Create or update a user from Google OAuth data."""
    existing_user = get_user_by_email(db, email)
    
    if existing_user:
        # Update existing user with Google info
        existing_user.google_id = google_id
        if name and not existing_user.full_name:
            existing_user.full_name = name
        if profile_picture:
            existing_user.profile_picture = profile_picture
        existing_user.updated_at = datetime.now()
        
        db.commit()
        db.refresh(existing_user)
        return existing_user
    else:
        # Create new user with Google info
        new_user = User(
            email=email,
            google_id=google_id,
            full_name=name,
            profile_picture=profile_picture,
            is_active=True,
            role=UserRole.USER
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    user = get_user_by_email(db, email)
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user_tokens(user: User):
    """Create access and refresh tokens for a user."""
    # Get the role as string
    role = str(user.role.value) if user.role else "user"
    
    access_token = create_access_token(
        subject=user.id,
        role=role
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        role=role
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def store_refresh_token(db: Session, user_id: str, refresh_token: str) -> None:
    """Store a refresh token in the database."""
    user = get_user_by_id(db, user_id)
    if user:
        user.refresh_token = refresh_token
        db.commit()


def user_to_response(user: User) -> UserResponse:
    """Convert a User model to a UserResponse model."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        role=user.role,
        created_at=user.created_at
    ) 