from sqlalchemy import Column, Integer, Float, Text
from app.database.db import Base


class PersonSession(Base):
    __tablename__ = "person_sessions"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    track_id       = Column(Integer, nullable=False, index=True)
    camera_id      = Column(Text,    nullable=False)
    first_seen     = Column(Text,    nullable=False)
    last_seen      = Column(Text,    nullable=False)
    total_duration = Column(Float,   nullable=False, default=0.0)
    last_state     = Column(Text,    nullable=True)

    def to_dict(self):
        return {
            "id":             self.id,
            "track_id":       self.track_id,
            "camera_id":      self.camera_id,
            "first_seen":     self.first_seen,
            "last_seen":      self.last_seen,
            "total_duration": round(self.total_duration, 1),
            "last_state":     self.last_state,
        }


class FatigueEvent(Base):
    """
    Replaces SleepEvent. Covers sleeping AND drowsy episodes.

    fatigue_type:  "sleeping" | "drowsy"
    fatigue_cause: human-readable explanation of WHY this record was created.
                   e.g. "Inactive 18s with reclined posture"
                        "No movement detected for 15s"
                        "Drowsy: still for 9s + reclined posture"
    """
    __tablename__ = "fatigue_events"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    person_id        = Column(Integer, nullable=True)
    camera_id        = Column(Text,    nullable=False)
    fatigue_type     = Column(Text,    nullable=False)   # "sleeping" | "drowsy"
    fatigue_cause    = Column(Text,    nullable=True)    # why this was created
    started_at       = Column(Text,    nullable=False)
    ended_at         = Column(Text,    nullable=True)
    duration         = Column(Float,   nullable=False)
    trigger          = Column(Text,    nullable=True)    # "inactivity"|"recline"|"drowsy"
    reclined_ratio   = Column(Float,   nullable=True)
    inactive_seconds = Column(Float,   nullable=True)
    confidence       = Column(Float,   nullable=True)
    snapshot         = Column(Text,    nullable=True)    # full annotated frame path
    crop_snapshot    = Column(Text,    nullable=True)    # cropped person thumbnail path
    summary          = Column(Text,    nullable=True)    # LLM summary

    def to_dict(self):
        return {
            "id":               self.id,
            "person_id":        self.person_id,
            "camera_id":        self.camera_id,
            "fatigue_type":     self.fatigue_type,
            "fatigue_cause":    self.fatigue_cause,
            "started_at":       self.started_at,
            "ended_at":         self.ended_at,
            "duration":         self.duration,
            "trigger":          self.trigger,
            "reclined_ratio":   self.reclined_ratio,
            "inactive_seconds": self.inactive_seconds,
            "confidence":       self.confidence,
            "snapshot":         self.snapshot,
            "crop_snapshot":    self.crop_snapshot,
            "summary":          self.summary,
        }