# app/schemas/ubicacion.py
from pydantic import BaseModel, Field
from typing import Optional

class UbicacionBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    tipo_zona: str = Field(..., max_length=50)
    descripcion: Optional[str] = None

class UbicacionCreate(UbicacionBase):
    pass

class UbicacionUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    tipo_zona: Optional[str] = Field(None, max_length=50)
    descripcion: Optional[str] = None

class UbicacionOut(UbicacionBase):
    id: int