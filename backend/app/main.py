from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import chat, files
from app.core.security import get_api_key # For global dependency if needed
from app.services.vector_store import initialize_vector_store, FAISS_INDEX_PATH # Corrected import
import os


app = FastAPI(title=settings.PROJECT_NAME)

# Configure CORS - Make sure we accept requests from browser origins
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
# Add localhost:3000 explicitly
if "http://localhost:3000" not in origins:
    origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
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

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

# Example of a globally protected endpoint (optional)
# @app.get("/secure-data", dependencies=[Depends(get_api_key)])
# async def secure_data():
#     return {"message": "This is secure data"}
