import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from docuquery_ai.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from docuquery_ai.models.db_models import User
from docuquery_ai.models.user import UserCreate, UserResponse, UserRole, UserUpdate


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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Generate a unique ID for the user
    user_id = str(uuid.uuid4())

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        id=user_id,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=user_data.is_active,
        role=user_data.role,
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        print(f"User created successfully: {db_user.id} - {db_user.email}")
        return db_user
    except Exception as e:
        db.rollback()
        print(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


def create_or_update_google_user(
    db: Session,
    email: str,
    google_id: str,
    name: Optional[str] = None,
    profile_picture: Optional[str] = None,
) -> User:
    """Create or update a user from Google OAuth data."""
    try:
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
            print(f"Updated existing user with Google data: {existing_user.id}")
            return existing_user
        else:
            # Create new user with Google info
            user_id = str(uuid.uuid4())
            new_user = User(
                id=user_id,
                email=email,
                google_id=google_id,
                full_name=name,
                profile_picture=profile_picture,
                is_active=True,
                role=UserRole.USER,
            )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            print(f"Created new user with Google data: {new_user.id}")
            return new_user
    except Exception as e:
        db.rollback()
        print(f"Error creating/updating Google user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create/update user with Google: {str(e)}",
        )


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

    access_token = create_access_token(subject=user.id, role=role)
    refresh_token = create_refresh_token(subject=user.id, role=role)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def store_refresh_token(db: Session, user_id: str, refresh_token: str) -> None:
    """Store a refresh token in the database."""
    try:
        user = get_user_by_id(db, user_id)
        if user:
            user.refresh_token = refresh_token
            db.commit()
            print(f"Stored refresh token for user: {user_id}")
        else:
            print(f"Cannot store refresh token - user not found: {user_id}")
    except Exception as e:
        db.rollback()
        print(f"Error storing refresh token: {str(e)}")


def user_to_response(user: User) -> UserResponse:
    """Convert a User model to a UserResponse model."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        role=user.role,
        created_at=user.created_at,
    )


def update_user(db: Session, user_id: str, user_data: UserUpdate) -> User:
    """Update a user's information."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update user fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.profile_picture is not None:
        user.profile_picture = user_data.profile_picture

    # Only admin can update role
    if user_data.role is not None and user_data.admin_action:
        user.role = user_data.role

    # Update password if provided
    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)

    user.updated_at = datetime.now()

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}",
        )


def get_all_users(db: Session) -> List[User]:
    """Get all users (admin function)."""
    return db.query(User).all()


def delete_user(db: Session, user_id: str) -> None:
    """Delete a user (admin function)."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    try:
        db.delete(user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )
