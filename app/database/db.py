from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_PATH

engine = create_engine(f"sqlite:///{DATABASE_PATH}")

SessionLocal = sessionmaker(bind=engine)