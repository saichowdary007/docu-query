import logging
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure logging only when run as a script
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "DocuQuery AI"
    API_KEY: str = os.getenv("API_KEY", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_PROJECT_ID: str = os.getenv("GOOGLE_PROJECT_ID", "")

    VECTOR_STORE_PATH: str = "./vector_db_data"
    TEMP_UPLOAD_FOLDER: str = "./temp_uploads"

    # Database settings
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    API_V1_STR: str = "/api/v1"


@lru_cache
def get_settings():
    logger.info("Loading settings...")
    return Settings()


settings = get_settings()
