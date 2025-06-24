import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "DocuQuery AI"
    API_V1_STR: str = "/api/v1"

    # Google Cloud settings - Required for functionality, but optional for testing
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "test-api-key")
    GOOGLE_PROJECT_ID: str = os.getenv("GOOGLE_PROJECT_ID", "test-project-id")
    GOOGLE_LOCATION: str = "us-central1"

    # For API Key Authentication - Required for functionality, but optional for testing
    API_KEY: str = os.getenv(
        "API_KEY", "test-security-key"
    )  # For securing your backend

    # For JWT Authentication - Required for functionality, but optional for testing
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "test-jwt-secret-key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database settings
    DATABASE_URL: str = "sqlite:///./app.db"

    VECTOR_STORE_PATH: str = "vector_db_data/"
    TEMP_UPLOAD_FOLDER: str = "temp_uploads/"

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
