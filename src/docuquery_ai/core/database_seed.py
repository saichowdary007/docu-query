import logging
import os
import uuid

from sqlalchemy.orm import Session

from docuquery_ai.core.database import get_db
from docuquery_ai.core.security import get_password_hash
from docuquery_ai.models.db_models import User
from docuquery_ai.models.user import UserRole

logger = logging.getLogger(__name__)


def seed_admin_user():
    """
    Seeds the database with an admin user if no users exist.
    Uses environment variables for credentials or defaults if not set.
    """
    # Get database session
    db = next(get_db())

    # Check if users exist
    user_count = db.query(User).count()

    if user_count > 0:
        logger.info("Users already exist in database. Skipping admin user creation.")
        return

    # Get admin credentials from environment variables or use defaults
    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@docuquery.ai")
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", "docuquery@admin2025")
    admin_name = os.getenv("SEED_ADMIN_NAME", "Admin User")

    # Generate admin user ID
    admin_id = str(uuid.uuid4())

    # Hash the password
    hashed_password = get_password_hash(admin_password)

    # Create the admin user
    admin_user = User(
        id=admin_id,
        email=admin_email,
        full_name=admin_name,
        hashed_password=hashed_password,
        is_active=True,
        role=UserRole.ADMIN,
    )

    try:
        # Add and commit to database
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        logger.info("Admin user created successfully: %s", admin_user.email)
        logger.info(
            "Please login with email: %s and password provided in environment",
            admin_email,
        )
    except (ValueError, IOError) as exc:
        db.rollback()
        logger.error("Error creating admin user: %s", str(exc))
