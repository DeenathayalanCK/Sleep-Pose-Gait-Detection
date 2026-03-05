import logging
from app.database.db import SessionLocal
from app.database.models import FatigueEvent, PersonSession

logger = logging.getLogger(__name__)


# ── PersonSession ─────────────────────────────────────────────────────────────

def upsert_person_session(track_id, camera_id, now_dt, state, elapsed):
    db = SessionLocal()
    try:
        row = (db.query(PersonSession)
               .filter(PersonSession.track_id == track_id,
                       PersonSession.camera_id == camera_id)
               .first())
        if row is None:
            db.add(PersonSession(
                track_id=track_id, camera_id=camera_id,
                first_seen=now_dt, last_seen=now_dt,
                total_duration=elapsed, last_state=state,
            ))
        else:
            row.last_seen      = now_dt
            row.total_duration = (row.total_duration or 0) + elapsed
            row.last_state     = state
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"upsert_person_session: {e}")
    finally:
        db.close()


def get_all_persons(camera_id=None):
    db = SessionLocal()
    try:
        q = db.query(PersonSession).order_by(PersonSession.track_id)
        if camera_id:
            q = q.filter(PersonSession.camera_id == camera_id)
        return q.all()
    finally:
        db.close()


# ── FatigueEvent ──────────────────────────────────────────────────────────────

def insert_fatigue_event(person_id, camera_id, fatigue_type, fatigue_cause,
                         started_at, ended_at, duration, trigger,
                         reclined_ratio, inactive_seconds, confidence,
                         snapshot, crop_snapshot, summary) -> "FatigueEvent | None":
    db = SessionLocal()
    try:
        ev = FatigueEvent(
            person_id=person_id, camera_id=camera_id,
            fatigue_type=fatigue_type, fatigue_cause=fatigue_cause,
            started_at=started_at, ended_at=ended_at,
            duration=duration, trigger=trigger,
            reclined_ratio=reclined_ratio,
            inactive_seconds=inactive_seconds,
            confidence=confidence,
            snapshot=snapshot, crop_snapshot=crop_snapshot,
            summary=summary,
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return ev
    except Exception as e:
        db.rollback()
        logger.error(f"insert_fatigue_event: {e}")
        return None
    finally:
        db.close()


def update_event_end(event_id, ended_at, duration, summary=None):
    db = SessionLocal()
    try:
        ev = db.query(FatigueEvent).filter(FatigueEvent.id == event_id).first()
        if ev:
            ev.ended_at = ended_at
            ev.duration = duration
            if summary:
                ev.summary = summary
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"update_event_end: {e}")
    finally:
        db.close()


def get_all_events():
    db = SessionLocal()
    try:
        return db.query(FatigueEvent).order_by(FatigueEvent.id.desc()).all()
    finally:
        db.close()