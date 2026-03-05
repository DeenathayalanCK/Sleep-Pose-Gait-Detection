from pydantic import BaseModel
from typing import Optional


# BUG FIX: schemas.py was empty — no response models existed
class FatigueEventSchema(BaseModel):
    id:        int
    timestamp: str
    duration:  float
    snapshot:  Optional[str] = None
    summary:   Optional[str] = None

    model_config = {"from_attributes": True}


class HealthSchema(BaseModel):
    status:  str
    service: str
