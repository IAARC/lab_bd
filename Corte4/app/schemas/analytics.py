# app/schemas/analytics.py
from datetime import date
from typing import List, Any
from pydantic import BaseModel

class CameraTrafficOut(BaseModel):
    operational_id: str
    from_date: date
    to_date: date
    traffic: List[Any]

class ZoneSummaryOut(BaseModel):
    zone_type: str
    summary: List[Any]

class AlertItemOut(BaseModel):
    operational_id: str
    severity: str
    total_alerts: int

class AlertsSummaryOut(BaseModel):
    days_analyzed: int
    data: List[AlertItemOut]
