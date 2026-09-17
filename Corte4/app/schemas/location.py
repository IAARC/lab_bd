# app/schemas/location.py
from pydantic import BaseModel, Field
from typing import Optional

class LocationBase(BaseModel):
    building: str = Field(..., max_length=255)
    floor: str = Field(..., max_length=10)
    zone_type: str = Field(..., max_length=255)

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    building: Optional[str] = Field(None, max_length=255)
    floor: Optional[str] = Field(None, max_length=10)
    zone_type: Optional[str] = Field(None, max_length=255)

class LocationOut(LocationBase):
    location_id: int