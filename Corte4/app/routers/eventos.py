from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from app.database import get_db
from app.schemas.evento import EventoCreate, EventoOut

router = APIRouter(prefix="/eventos", tags=["Eventos"])

@router.get("", response_model=list[EventoOut])
def list_eventos(db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT id, id_camara, tipo_objeto, confianza, fecha_hora FROM eventos ORDER BY fecha_hora DESC LIMIT 100;")
        return cur.fetchall()

@router.get("/{id}", response_model=EventoOut)
def get_evento(id: int, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT id, id_camara, tipo_objeto, confianza, fecha_hora FROM eventos WHERE id = %s;", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evento no encontrado")
        return row

@router.post("", response_model=EventoOut, status_code=status.HTTP_201_CREATED)
def create_evento(payload: EventoCreate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        embedding_val = str(payload.embedding) if payload.embedding else None
        cur.execute(
            """
            INSERT INTO eventos (id_camara, tipo_objeto, confianza, embedding, fecha_hora)
            VALUES (%s, %s, %s, %s::vector, COALESCE(%s, CURRENT_TIMESTAMP))
            RETURNING id, id_camara, tipo_objeto, confianza, fecha_hora;
            """,
            (payload.id_camara, payload.tipo_objeto, payload.confianza, embedding_val, payload.fecha_hora)
        )
        new_row = cur.fetchone()
        db.commit()
        return new_row