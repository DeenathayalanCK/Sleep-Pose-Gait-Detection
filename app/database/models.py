from sqlalchemy import Column, Integer, Float, Text
from app.database.db import Base


class SleepEvent(Base):
    __tablename__ = "sleep_events"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    camera_id        = Column(Text,    nullable=False)
    started_at       = Column(Text,    nullable=False)   # ISO timestamp
    ended_at         = Column(Text,    nullable=True)    # filled on episode end
    duration         = Column(Float,   nullable=False)
    trigger          = Column(Text,    nullable=True)    # "inactivity" | "recline"
    reclined_ratio   = Column(Float,   nullable=True)
    inactive_seconds = Column(Float,   nullable=True)
    confidence       = Column(Float,   nullable=True)
    snapshot         = Column(Text,    nullable=True)    # path to keyframe
    summary          = Column(Text,    nullable=True)    # LLM summary

    def to_dict(self):
        return {
            "id":               self.id,
            "camera_id":        self.camera_id,
            "started_at":       self.started_at,
            "ended_at":         self.ended_at,
            "duration":         self.duration,
            "trigger":          self.trigger,
            "reclined_ratio":   self.reclined_ratio,
            "inactive_seconds": self.inactive_seconds,
            "confidence":       self.confidence,
            "snapshot":         self.snapshot,
            "summary":          self.summary,
        }