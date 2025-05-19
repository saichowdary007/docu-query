from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import chat, files, auth
from app.core.security import get_api_key # For global dependency if needed
from app.services.vector_store import initialize_vector_store, FAISS_INDEX_PATH # Corrected import
from app.core.database import Base, engine, init_db
import os


# We're moving database initialization to startup event, so remove this line
# init_db()

app = FastAPI(title=settings.PROJECT_NAME)

# Configure CORS for different environments
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
# Add development and production origins
default_origins = [
    "http://localhost:3000",
    "http://frontend:3000",    # Add Docker container service name for docker-compose networking
    "https://docuquery-ai.vercel.app",     # Production Vercel URL
    "https://docuquery-ai-git-main.vercel.app",  # Vercel preview branch URL
]

# Add default origins if not already included
for origin in default_origins:
    if origin not in origins:
        origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-KEY"],
)

@app.on_event("startup")
async def startup_event():
    # Initialize database tables
    init_db()
    
    # Initialize vector store on startup if index exists
    # This avoids re-initializing an empty one if data is already there.
    if os.path.exists(FAISS_INDEX_PATH) and os.listdir(FAISS_INDEX_PATH):
        print("Attempting to load existing vector store on startup...")
        initialize_vector_store() # Will load existing if path is valid
    else:
        print("No existing vector store found on startup. Will be created on first file upload.")
    
    # Create temp upload folder if it doesn't exist
    os.makedirs(settings.TEMP_UPLOAD_FOLDER, exist_ok=True)
    print(f"Temp upload folder: {settings.TEMP_UPLOAD_FOLDER}")
    print(f"CORS origins: {origins}")


app.include_router(files.router, prefix=settings.API_V1_STR + "/files", tags=["Files"])
app.include_router(chat.router, prefix=settings.API_V1_STR + "/chat", tags=["Chat"])
app.include_router(auth.router, prefix=settings.API_V1_STR + "/auth", tags=["Auth"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

# Example of a globally protected endpoint (optional)
# @app.get("/secure-data", dependencies=[Depends(get_api_key)])
# async def secure_data():
#     return {"message": "This is secure data"}
