# app/schemas/analytics.py
from datetime import date
from typing import List, Any
from pydantic import BaseModel

class CameraTrafficOut(BaseModel):
    camera_id: int
    from_date: date
    to_date: date
    traffic: List[Any]

class ZoneSummaryOut(BaseModel):
    tipo_zona: str
    summary: List[Any]

class AlertItemOut(BaseModel):
    id_camara: int
    camara_codigo: str
    severidad: str
    total_alertas: int

class AlertsSummaryOut(BaseModel):
    days_analyzed: int
    data: List[AlertItemOut]
