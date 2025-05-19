from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any
from jose import jwt, JWTError
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, create_access_token, SECRET_KEY, ALGORITHM
from app.models.user import UserCreate, UserLogin, UserResponse, TokenData, GoogleAuthRequest
from app.services.user_service import (
    authenticate_user, create_user, get_user_by_id, user_to_response,
    create_user_tokens, create_or_update_google_user, store_refresh_token
)
from app.services.google_auth_service import verify_google_token, GoogleAuthException

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Register a new user.
    """
    db_user = create_user(db, user_data)
    return user_to_response(db_user)


@router.post("/login", response_model=TokenData)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Login with username (email) and password.
    Returns JWT tokens for authentication.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = create_user_tokens(user)
    # Optionally store refresh token in database
    store_refresh_token(db, user.id, tokens["refresh_token"])
    
    return tokens


@router.post("/google", response_model=TokenData)
async def google_auth(
    data: GoogleAuthRequest = Body(...),
    db: Session = Depends(get_db)
) -> Any:
    """
    Authenticate with Google by providing a Google ID token.
    Returns JWT tokens for authentication.
    """
    try:
        # Verify the Google token
        token_info = await verify_google_token(data.token)
        
        # Extract user information
        email = token_info.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found in Google token"
            )
        
        google_id = token_info.get("sub")
        name = token_info.get("name")
        picture = token_info.get("picture")
        
        # Create or update user with Google information
        user = create_or_update_google_user(
            db, email, google_id, name, picture
        )
        
        # Generate tokens
        tokens = create_user_tokens(user)
        store_refresh_token(db, user.id, tokens["refresh_token"])
        
        return tokens
    
    except GoogleAuthException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=TokenData)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token.
    """
    try:
        # Manually decode the token instead of using get_current_user
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = get_user_by_id(db, user_id)
        if not user or user.refresh_token != refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate new tokens
        tokens = create_user_tokens(user)
        store_refresh_token(db, user.id, tokens["refresh_token"])
        
        return tokens
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    token_data = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get current user information.
    """
    user = get_user_by_id(db, token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_to_response(user) 