import sqlite3

from sqlalchemy import create_engine, exc, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

from docuquery_ai.core.config import settings

# Get database URL from centralized settings
DATABASE_URL = settings.DATABASE_URL

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


def init_db():
    """
    Initialize database tables safely using checkfirst=True and refined error handling.
    """
    try:
        # Use checkfirst=True to prevent "table already exists" errors.
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print(
            "Database tables checked/initialized successfully using create_all(checkfirst=True)."
        )

    except exc.OperationalError as op_err:
        # This block handles OperationalErrors.
        # We check if it's an "already exists" error, which might occur if checkfirst=True
        # isn't foolproof in extreme concurrency or for certain DB driver behaviors.
        error_message_lower = str(op_err).lower()
        orig_error_message_lower = ""
        if hasattr(op_err, "orig") and op_err.orig is not None:
            orig_error_message_lower = str(op_err.orig).lower()

        if (
            "table" in error_message_lower and "already exist" in error_message_lower
        ) or (
            "table" in orig_error_message_lower
            and "already exist" in orig_error_message_lower
        ):
            print(
                f"Tables already exist (OperationalError caught, treated as benign due to checkfirst=True): {op_err}"
            )
        else:
            # Any other OperationalError should be raised.
            print(
                f"A non-'already exists' OperationalError occurred during DB initialization: {op_err}"
            )
            raise
    except Exception as e:  # Catch any other type of exception during DB init
        print(f"An unexpected error occurred during DB initialization: {str(e)}")
        raise


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
