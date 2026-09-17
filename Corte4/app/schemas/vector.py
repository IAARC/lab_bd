# app/schemas/vector.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchSimilarBody(BaseModel):
    embedding: List[float] = Field(..., min_length=512, max_length=512)

class SimilarObjectOut(BaseModel):
    id: int
    tipo_objeto: str
    id_camara: int
    fecha_hora: datetime
    distancia: float