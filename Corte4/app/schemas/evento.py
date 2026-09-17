# app/schemas/evento.py
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class EventoCreate(BaseModel):
    id_camara: int
    tipo_objeto: str = Field(..., max_length=50) # 'persona', 'vehiculo', etc.
    confianza: float = Field(..., ge=0.0, le=1.0)
    embedding: Optional[List[float]] = None # Vector 512d
    fecha_hora: Optional[datetime] = None

class EventoOut(BaseModel):
    id: int
    id_camara: int
    tipo_objeto: str
    confianza: float
    fecha_hora: datetime