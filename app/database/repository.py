import logging
from app.database.db import SessionLocal
from app.database.models import FatigueEvent

logger = logging.getLogger(__name__)


def insert_event(timestamp: str, duration: float, snapshot: str, summary: str):
    # BUG FIX: original used raw text SQL with manual CREATE TABLE on every
    # call and relied on sqlalchemy 1.x dict(row) which breaks in SA 2.x.
    db = SessionLocal()
    try:
        event = FatigueEvent(
            timestamp=timestamp,
            duration=duration,
            snapshot=snapshot,
            summary=summary,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception as e:
        db.rollback()
        logger.error(f"DB insert error: {e}")
        return None
    finally:
        db.close()


def get_all_events():
    db = SessionLocal()
    try:
        return db.query(FatigueEvent).order_by(FatigueEvent.id.desc()).all()
    finally:
        db.close()
