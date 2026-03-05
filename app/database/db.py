import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import DATABASE_PATH

logger = logging.getLogger(__name__)

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def init_db():
    from app.database.models import FatigueEvent  # noqa
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised.")