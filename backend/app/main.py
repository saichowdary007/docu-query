from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from app.core.config import settings
from app.core.database import init_db
from app.core.database_migration import run_migrations
from app.core.database_seed import seed_admin_user
from app.routers import auth, files, queries, users

app = FastAPI(
    title="DocuQuery AI",
    description="AI-powered document query service",
    version="0.1.0",
)

# Configure CORS
default_origins = [
    "http://localhost:3000",  # Local Next.js frontend
    "http://frontend:3000",   # Docker setup
    "https://docuquery-ai.vercel.app", # Vercel frontend
    "https://docuquery-ai-git-main-vercel.app", # Vercel preview deployments
]

# Enable environment-based CORS origins
additional_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
all_origins = default_origins + [o for o in additional_origins if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=all_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(files.router, prefix=f"{settings.API_V1_STR}/files", tags=["files"])
app.include_router(queries.router, prefix=f"{settings.API_V1_STR}/queries", tags=["queries"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])

@app.on_event("startup")
async def startup_event():
    """
    Initialize the database on startup.
    """
    # Initialize database tables
    init_db()
    
    # Seed admin user if database is empty
    seed_admin_user()
    
    # Run data migrations
    run_migrations()
    
    # Initialize vector store
    from app.services.vector_store import initialize_vector_store
    initialize_vector_store()
    
    # Ensure temp upload folder exists
    os.makedirs(settings.TEMP_UPLOAD_FOLDER, exist_ok=True)
    
    print(f"Temp upload folder: {settings.TEMP_UPLOAD_FOLDER}")
    print(f"CORS origins: {all_origins}")

@app.get("/")
async def root():
    return {"message": "Welcome to DocuQuery AI!", "status": "running"}
