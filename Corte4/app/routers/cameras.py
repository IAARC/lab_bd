# app/routers/cameras.py
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from app.database import get_db
from app.schemas.camera import CameraCreate, CameraUpdate, CameraOut

router = APIRouter(prefix="/camaras", tags=["Camaras"])

@router.get("", response_model=list[CameraOut])
def list_cameras(db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT operational_id, device_model, has_night_vision, operating_status, camera_name, location_id FROM monitoring.camera ORDER BY operational_id ASC;")
        return cur.fetchall()

@router.get("/{id}", response_model=CameraOut)
def get_camera(id: str, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT operational_id, device_model, has_night_vision, operating_status, camera_name, location_id FROM monitoring.camera WHERE operational_id = %s;", (id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Camera not found")
        return row

@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
def create_camera(payload: CameraCreate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO monitoring.camera (operational_id, device_model, has_night_vision, operating_status, camera_name, location_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING operational_id, device_model, has_night_vision, operating_status, camera_name, location_id;
            """,
            (payload.operational_id, payload.device_model, payload.has_night_vision, payload.operating_status, payload.camera_name, payload.location_id)
        )
        new_row = cur.fetchone()
        db.commit()
        return new_row

@router.put("/{id}", response_model=CameraOut)
def update_camera(id: str, payload: CameraUpdate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE monitoring.camera
            SET device_model = COALESCE(%s, device_model),
                has_night_vision = COALESCE(%s, has_night_vision),
                operating_status = COALESCE(%s, operating_status),
                camera_name = COALESCE(%s, camera_name),
                location_id = COALESCE(%s, location_id)
            WHERE operational_id = %s
            RETURNING operational_id, device_model, has_night_vision, operating_status, camera_name, location_id;
            """,
            (payload.device_model, payload.has_night_vision, payload.operating_status, payload.camera_name, payload.location_id, id)
        )
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Camera not found")
        db.commit()
        return updated