# app/schemas/vector.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchSimilarBody(BaseModel):
    embedding: List[float] = Field(..., min_length=512, max_length=512)

class SimilarObjectOut(BaseModel):
    object_id: int
    general_category: str
    operational_id: str
    timestamp: datetime
    distance: float