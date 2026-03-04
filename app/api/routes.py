from fastapi import APIRouter
from sqlalchemy import text
from app.database.db import engine

router = APIRouter()

@router.get("/events")
def get_events():

    with engine.connect() as conn:

        result = conn.execute(text("SELECT * FROM fatigue_events"))

        return [dict(r) for r in result]