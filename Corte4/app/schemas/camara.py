# app/schemas/camara.py
from pydantic import BaseModel, Field
from typing import Optional

class CamaraBase(BaseModel):
    codigo: str = Field(..., max_length=50)
    modelo: Optional[str] = Field(None, max_length=100)
    estado: str = Field("activa", max_length=20)
    id_ubicacion: int

class CamaraCreate(CamaraBase):
    pass

class CamaraUpdate(BaseModel):
    modelo: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=20)
    id_ubicacion: Optional[int] = None

class CamaraOut(CamaraBase):
    id: int