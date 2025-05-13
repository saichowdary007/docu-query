from fastapi import APIRouter, Depends
from ..core.security import api_key_auth
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for deployment platforms to monitor the application's status.
    """
    return {"status": "healthy", "message": "Service is running normally"}

@router.get("/health/protected", tags=["health"], dependencies=[Depends(api_key_auth)])
async def protected_health_check():
    """
    Protected health check endpoint that requires API key authentication.
    Useful for checking if authentication is working properly.
    """
    return {"status": "healthy", "message": "Authentication is working properly"} 