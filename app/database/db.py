import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_PATH

logger = logging.getLogger(__name__)

# BUG FIX: database directory was never created — SQLAlchemy raises
# OperationalError("unable to open database file") on first run.
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},  # needed for multi-thread use
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db():
    """Create all tables on startup."""
    from app.database.models import FatigueEvent  # noqa: F401 — registers model
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised.")
