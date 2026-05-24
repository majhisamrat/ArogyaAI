from sqlalchemy.orm import sessionmaker
from database.models import engine

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """
    Get a database session directly (non-generator version).
    Always call session.close() after use.
    """
    return SessionLocal()