# app/routers/locations.py
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from app.database import get_db
from app.schemas.location import LocationCreate, LocationUpdate, LocationOut

router = APIRouter(prefix="/ubicaciones", tags=["Ubicaciones"])

@router.get("", response_model=list[LocationOut])
def list_locations(db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT location_id, building, floor, zone_type FROM monitoring.location ORDER BY location_id ASC;")
        return cur.fetchall()

@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(payload: LocationCreate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO monitoring.location (location_id, building, floor, zone_type)
            VALUES ((SELECT COALESCE(MAX(location_id), 0) + 1 FROM monitoring.location), %s, %s, %s)
            RETURNING location_id, building, floor, zone_type;
            """,
            (payload.building, payload.floor, payload.zone_type)
        )
        new_row = cur.fetchone()
        db.commit()
        return new_row

@router.put("/{id}", response_model=LocationOut)
def update_location(id: int, payload: LocationUpdate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE monitoring.location
            SET building = COALESCE(%s, building),
                floor = COALESCE(%s, floor),
                zone_type = COALESCE(%s, zone_type)
            WHERE location_id = %s
            RETURNING location_id, building, floor, zone_type;
            """,
            (payload.building, payload.floor, payload.zone_type, id)
        )
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Location not found")
        db.commit()
        return updated

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(id: int, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("DELETE FROM monitoring.location WHERE location_id = %s RETURNING location_id;", (id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Location not found")
        db.commit()