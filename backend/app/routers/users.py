from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import UserResponse, UserUpdate
from app.services.user_service import (
    get_user_by_id, user_to_response, update_user,
    get_all_users, delete_user
)

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_my_info(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    user = get_user_by_id(db, current_user.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user_to_response(user)

@router.put("/me", response_model=UserResponse)
async def update_my_info(
    user_data: UserUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    user = get_user_by_id(db, current_user.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    updated_user = update_user(db, user.id, user_data)
    return user_to_response(updated_user)

@router.get("/", response_model=List[UserResponse])
async def get_users(
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    users = get_all_users(db)
    return [user_to_response(user) for user in users]

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user_to_response(user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: str,
    admin_user = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete user by ID (admin only)"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    delete_user(db, user_id)
    return None 