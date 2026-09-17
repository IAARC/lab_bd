# app/routers/vector.py
from fastapi import APIRouter, Depends, Query, HTTPException
from psycopg import Connection
from app.database import get_db
from app.schemas.vector import SearchSimilarBody, SimilarObjectOut

router = APIRouter(tags=["Vectores"])

@router.get("/objects/{id}/similar", response_model=list[SimilarObjectOut])
def get_similar_objects(
    id: int,
    threshold: float = Query(0.20, ge=0.0, le=2.0),
    limit: int = Query(5, ge=1, le=100),
    db: Connection = Depends(get_db)
):
    with db.cursor() as cur:
        cur.execute("SELECT objeto_encontrado_id, tipo, distancia_coseno, camara_origen, fecha_evento FROM monitoring.find_similar_objects(%s, %s, %s);", (id, threshold, limit))
        results = cur.fetchall()
        
        out = []
        for r in results:
            out.append({
                "object_id": r["objeto_encontrado_id"],
                "general_category": r["tipo"],
                "distance": r["distancia_coseno"],
                "operational_id": r["camara_origen"],
                "timestamp": r["fecha_evento"]
            })
        return out

@router.post("/search/similar", response_model=list[SimilarObjectOut])
def search_similar_by_embedding(
    payload: SearchSimilarBody,
    tipo: str = Query(None, pattern="^(PERSON|VEHICLE)$"),
    limit: int = Query(10, ge=1, le=50),
    db: Connection = Depends(get_db)
):
    embedding_str = "[" + ",".join(map(str, payload.embedding)) + "]"
    
    tipo_filtro = tipo.upper() if tipo else None

    query = """
        SELECT 
            oe.object_id,
            dobj.general_category,
            c.operational_id,
            de.timestamp_triggered AS timestamp,
            (oe.visual_embedding <=> %s::vector) AS distance
        FROM monitoring.object_embedding oe
        JOIN monitoring.detected_object dobj ON oe.object_id = dobj.object_id
        JOIN monitoring.detection_event de ON dobj.event_id = de.event_id
        JOIN monitoring.camera c ON de.operational_id = c.operational_id
        WHERE (%s::VARCHAR IS NULL OR dobj.general_category = %s)
        ORDER BY distance ASC
        LIMIT %s;
    """
    with db.cursor() as cur:
        cur.execute(query, (embedding_str, tipo_filtro, tipo_filtro, limit))
        rows = cur.fetchall()
        return rows