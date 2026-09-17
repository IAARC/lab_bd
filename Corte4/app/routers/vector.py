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
        # Invocación directa de la función PL/pgSQL de Fase 3
        cur.execute("SELECT * FROM find_similar_objects(%s, %s, %s);", (id, threshold, limit))
        results = cur.fetchall()
        return results

@router.post("/search/similar", response_model=list[SimilarObjectOut])
def search_similar_by_embedding(
    payload: SearchSimilarBody,
    tipo: str = Query(None, pattern="^(persona|vehiculo|vehículo)$"),
    limit: int = Query(10, ge=1, le=50),
    db: Connection = Depends(get_db)
):
    # Formateo del array a la sintaxis esperada por pgvector: '[0.12, 0.34, ...]'
    embedding_str = "[" + ",".join(map(str, payload.embedding)) + "]"
    
    # Normalizar por si se consulta con o sin tilde
    tipo_filtro = tipo.lower() if tipo else None
    if tipo_filtro == "vehículo":
        tipo_filtro = "vehiculo"

    query = """
        SELECT 
            e.id,
            e.tipo_objeto,
            e.id_camara,
            e.fecha_hora,
            (e.embedding <=> %s::vector) AS distancia
        FROM eventos e
        WHERE (%s IS NULL OR e.tipo_objeto = %s)
          AND e.embedding IS NOT NULL
        ORDER BY distancia ASC
        LIMIT %s;
    """
    with db.cursor() as cur:
        cur.execute(query, (embedding_str, tipo_filtro, tipo_filtro, limit))
        rows = cur.fetchall()
        return rows