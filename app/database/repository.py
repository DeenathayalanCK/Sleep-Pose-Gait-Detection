import logging
from app.database.db import SessionLocal
from app.database.models import SleepEvent

logger = logging.getLogger(__name__)


def insert_event(camera_id, started_at, ended_at, duration,
                 trigger, reclined_ratio, inactive_seconds,
                 confidence, snapshot, summary) -> SleepEvent | None:
    db = SessionLocal()
    try:
        event = SleepEvent(
            camera_id=camera_id,
            started_at=started_at,
            ended_at=ended_at,
            duration=duration,
            trigger=trigger,
            reclined_ratio=reclined_ratio,
            inactive_seconds=inactive_seconds,
            confidence=confidence,
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


def update_event_end(event_id: int, ended_at: str, duration: float,
                     summary: str) -> None:
    """Called when a sleep episode ends — fills ended_at and final duration."""
    db = SessionLocal()
    try:
        event = db.query(SleepEvent).filter(SleepEvent.id == event_id).first()
        if event:
            event.ended_at = ended_at
            event.duration = duration
            event.summary  = summary
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"DB update error: {e}")
    finally:
        db.close()


def get_all_events():
    db = SessionLocal()
    try:
        return db.query(SleepEvent).order_by(SleepEvent.id.desc()).all()
    finally:
        db.close()