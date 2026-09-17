# app/routers/ubicaciones.py
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from app.database import get_db
from app.schemas.ubicacion import UbicacionCreate, UbicacionUpdate, UbicacionOut

router = APIRouter(prefix="/ubicaciones", tags=["Ubicaciones"])

@router.get("", response_model=list[UbicacionOut])
def list_ubicaciones(db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT id, nombre, tipo_zona, descripcion FROM ubicaciones ORDER BY id ASC;")
        return cur.fetchall()

@router.post("", response_model=UbicacionOut, status_code=status.HTTP_201_CREATED)
def create_ubicacion(payload: UbicacionCreate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ubicaciones (nombre, tipo_zona, descripcion)
            VALUES (%s, %s, %s)
            RETURNING id, nombre, tipo_zona, descripcion;
            """,
            (payload.nombre, payload.tipo_zona, payload.descripcion)
        )
        new_row = cur.fetchone()
        db.commit()
        return new_row

@router.put("/{id}", response_model=UbicacionOut)
def update_ubicacion(id: int, payload: UbicacionUpdate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE ubicaciones
            SET nombre = COALESCE(%s, nombre),
                tipo_zona = COALESCE(%s, tipo_zona),
                descripcion = COALESCE(%s, descripcion)
            WHERE id = %s
            RETURNING id, nombre, tipo_zona, descripcion;
            """,
            (payload.nombre, payload.tipo_zona, payload.descripcion, id)
        )
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Ubicación no encontrada")
        db.commit()
        return updated

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ubicacion(id: int, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("DELETE FROM ubicaciones WHERE id = %s RETURNING id;", (id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Ubicación no encontrada")
        db.commit()