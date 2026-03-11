"""
db.py — Database engine setup.

PostgreSQL in production (set DATABASE_URL in .env).
Falls back to SQLite automatically if DATABASE_URL is not set,
so local dev / first-run still works without a Postgres container.

PostgreSQL URL format:
  DATABASE_URL=postgresql://user:password@host:5432/dbname
  (docker-compose sets this via environment automatically)
"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import DATABASE_URL, DATABASE_PATH

logger = logging.getLogger(__name__)


def _build_engine():
    url = DATABASE_URL

    if url and url.startswith("postgresql"):
        logger.info(f"Database: PostgreSQL @ {url.split('@')[-1]}")
        return create_engine(
            url,
            pool_size        = 5,
            max_overflow     = 10,
            pool_pre_ping    = True,   # detect stale connections
            pool_recycle     = 300,    # recycle connections every 5 min
            connect_args     = {},
        )
    else:
        # SQLite fallback — single-writer, fine for dev/testing
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        sqlite_url = f"sqlite:///{DATABASE_PATH}"
        logger.warning(
            f"DATABASE_URL not set — using SQLite at {DATABASE_PATH}. "
            "Set DATABASE_URL=postgresql://... for production."
        )
        return create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
        )


engine       = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db():
    from app.database.models import FatigueEvent, PersonSession, GroundTruthLabel  # noqa
    Base.metadata.create_all(bind=engine)

    # Verify connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise