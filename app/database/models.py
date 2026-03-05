from sqlalchemy import Column, Integer, Float, Text
from app.database.db import Base


# BUG FIX: models.py was completely empty — no table definition existed.
# repository.py was manually running CREATE TABLE each insert (fragile) and
# using raw SQL while the rest of the app expected ORM.
class FatigueEvent(Base):
    __tablename__ = "fatigue_events"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(Text, nullable=False)
    duration  = Column(Float, nullable=False)
    snapshot  = Column(Text, nullable=True)
    summary   = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id":        self.id,
            "timestamp": self.timestamp,
            "duration":  self.duration,
            "snapshot":  self.snapshot,
            "summary":   self.summary,
        }
