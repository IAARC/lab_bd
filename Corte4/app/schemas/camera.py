# app/schemas/camera.py
from pydantic import BaseModel, Field
from typing import Optional

class CameraBase(BaseModel):
    operational_id: str = Field(..., max_length=55)
    device_model: str = Field(..., max_length=55)
    has_night_vision: bool = False
    operating_status: str = Field("active", max_length=55)
    camera_name: Optional[str] = Field(None, max_length=100)
    location_id: int

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    device_model: Optional[str] = Field(None, max_length=55)
    has_night_vision: Optional[bool] = None
    operating_status: Optional[str] = Field(None, max_length=55)
    camera_name: Optional[str] = Field(None, max_length=100)
    location_id: Optional[int] = None

class CameraOut(CameraBase):
    pass