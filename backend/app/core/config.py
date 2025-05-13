from pydantic_settings import BaseSettings
import os
from typing import Optional, Union
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Chatbot"
    API_V1_STR: str = "/api/v1"
    
    GOOGLE_API_KEY: Union[str, None] = os.getenv("GOOGLE_API_KEY") # Or use service account json path
    GOOGLE_PROJECT_ID: Union[str, None] = os.getenv("GOOGLE_PROJECT_ID")
    GOOGLE_LOCATION: str = os.getenv("GOOGLE_LOCATION", "us-central1") # e.g., us-central1

    # For API Key Authentication
    API_KEY: str = os.getenv("BACKEND_API_KEY", "your-secret-api-key") # For securing your backend
    
    VECTOR_STORE_PATH: str = "vector_db_data/"
    TEMP_UPLOAD_FOLDER: str = "temp_uploads/"

    class Config:
        case_sensitive = True

settings = Settings()
