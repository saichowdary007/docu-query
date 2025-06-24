from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "DocuQuery AI"
    API_V1_STR: str = "/api/v1"
    
    # Google Cloud settings - MUST be provided in the environment
    GOOGLE_API_KEY: str
    GOOGLE_PROJECT_ID: str
    GOOGLE_LOCATION: str = "us-central1"

    # For API Key Authentication - MUST be provided in the environment
    API_KEY: str # For securing your backend
    
    # For JWT Authentication - MUST be provided in the environment
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database settings
    DATABASE_URL: str = "sqlite:///./app.db"

    VECTOR_STORE_PATH: str = "vector_db_data/"
    TEMP_UPLOAD_FOLDER: str = "temp_uploads/"

    class Config:
        case_sensitive = True
        # Pydantic will automatically read from .env files if python-dotenv is installed
        # and the .env file is in the right place.
        # This makes load_dotenv() call at the top redundant if you manage env vars correctly.
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
