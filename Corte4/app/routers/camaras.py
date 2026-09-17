from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from app.database import get_db
from app.schemas.camara import CamaraCreate, CamaraUpdate, CamaraOut

router = APIRouter(prefix="/camaras", tags=["Cámaras"])

@router.get("", response_model=list[CamaraOut])
def list_camaras(db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT id, codigo, modelo, estado, id_ubicacion FROM camaras ORDER BY id ASC;")
        return cur.fetchall()

@router.get("/{id}", response_model=CamaraOut)
def get_camara(id: int, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT id, codigo, modelo, estado, id_ubicacion FROM camaras WHERE id = %s;", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cámara no encontrada")
        return row

@router.post("", response_model=CamaraOut, status_code=status.HTTP_201_CREATED)
def create_camara(payload: CamaraCreate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO camaras (codigo, modelo, estado, id_ubicacion)
            VALUES (%s, %s, %s, %s)
            RETURNING id, codigo, modelo, estado, id_ubicacion;
            """,
            (payload.codigo, payload.modelo, payload.estado, payload.id_ubicacion)
        )
        new_row = cur.fetchone()
        db.commit()
        return new_row

@router.put("/{id}", response_model=CamaraOut)
def update_camara(id: int, payload: CamaraUpdate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE camaras
            SET modelo = COALESCE(%s, modelo),
                estado = COALESCE(%s, estado),
                id_ubicacion = COALESCE(%s, id_ubicacion)
            WHERE id = %s
            RETURNING id, codigo, modelo, estado, id_ubicacion;
            """,
            (payload.modelo, payload.estado, payload.id_ubicacion, id)
        )
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Cámara no encontrada")
        db.commit()
        return updated