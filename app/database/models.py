"""
models.py — All SQLAlchemy ORM models.

Tables:
  person_sessions  — per-person session tracking (existing)
  fatigue_events   — detected sleep/drowsy episodes (existing)
  ground_truth_labels — human-labelled ground truth for evaluation (NEW)
"""
from sqlalchemy import Column, Integer, Float, Text, Boolean, Index
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
    Detected fatigue episode. fatigue_type = sleeping | drowsy.
    summary now stores structured risk score string (not LLM output).
    """
    __tablename__ = "fatigue_events"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    person_id        = Column(Integer, nullable=True,  index=True)
    camera_id        = Column(Text,    nullable=False,  index=True)
    fatigue_type     = Column(Text,    nullable=False)
    fatigue_cause    = Column(Text,    nullable=True)
    started_at       = Column(Text,    nullable=False,  index=True)
    ended_at         = Column(Text,    nullable=True)
    duration         = Column(Float,   nullable=False)
    trigger          = Column(Text,    nullable=True)
    reclined_ratio   = Column(Float,   nullable=True)
    inactive_seconds = Column(Float,   nullable=True)
    confidence       = Column(Float,   nullable=True)
    snapshot         = Column(Text,    nullable=True)
    crop_snapshot    = Column(Text,    nullable=True)
    summary          = Column(Text,    nullable=True)

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


class GroundTruthLabel(Base):
    """
    Human-labelled ground truth for evaluation metrics.

    Workflow:
      1. Reviewer watches the Records tab snapshot/crop
      2. For each detected event: marks it TRUE_POSITIVE or FALSE_POSITIVE
      3. For missed real events: adds a FALSE_NEGATIVE record manually
      4. Evaluation module reads these labels to compute precision/recall/F1

    label_type:
      "TP" — system detected it, reviewer confirms it was real
      "FP" — system detected it, reviewer says it was wrong
      "FN" — system missed it, reviewer adds it manually
    """
    __tablename__ = "ground_truth_labels"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    event_id       = Column(Integer, nullable=True,  index=True)
                     # FK to fatigue_events.id (nullable for FN entries)
    person_id      = Column(Integer, nullable=True)
    camera_id      = Column(Text,    nullable=False)
    label_type     = Column(Text,    nullable=False)  # "TP" | "FP" | "FN"
    fatigue_type   = Column(Text,    nullable=False)  # "sleeping" | "drowsy"
    started_at     = Column(Text,    nullable=False)  # actual event start
    ended_at       = Column(Text,    nullable=True)
    duration       = Column(Float,   nullable=True)   # actual duration (seconds)
    notes          = Column(Text,    nullable=True)   # reviewer comments
    labelled_by    = Column(Text,    nullable=True)   # reviewer name
    labelled_at    = Column(Text,    nullable=True)   # when label was added
    detection_lag  = Column(Float,   nullable=True)
                     # seconds from actual onset to first system alert (latency)

    __table_args__ = (
        Index("ix_gtl_camera_type", "camera_id", "fatigue_type"),
    )

    def to_dict(self):
        return {
            "id":            self.id,
            "event_id":      self.event_id,
            "person_id":     self.person_id,
            "camera_id":     self.camera_id,
            "label_type":    self.label_type,
            "fatigue_type":  self.fatigue_type,
            "started_at":    self.started_at,
            "ended_at":      self.ended_at,
            "duration":      self.duration,
            "notes":         self.notes,
            "labelled_by":   self.labelled_by,
            "labelled_at":   self.labelled_at,
            "detection_lag": self.detection_lag,
        }