# app/schemas/event.py
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class EventCreate(BaseModel):
    operational_id: str = Field(..., max_length=55)
    general_category: str = Field(..., max_length=255) # 'PERSON', 'VEHICLE'
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    embedding: Optional[List[float]] = None # Vector 512d
    timestamp: Optional[datetime] = None
    vehicle_type: Optional[str] = Field(None, max_length=255)
    license_plate: Optional[str] = Field(None, max_length=20)
    baggage_type: Optional[str] = Field(None, max_length=255)

class EventOut(BaseModel):
    event_id: int
    object_id: int
    operational_id: str
    general_category: str
    confidence_score: float
    timestamp: datetime