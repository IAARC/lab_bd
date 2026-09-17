# app/routers/events.py
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection
from app.database import get_db
from app.schemas.event import EventCreate, EventOut

router = APIRouter(prefix="/eventos", tags=["Eventos"])

@router.get("", response_model=list[EventOut])
def list_events(db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("""
            SELECT e.event_id, o.object_id, e.operational_id, o.general_category, e.confidence_level AS confidence_score, e.timestamp_triggered AS timestamp 
            FROM monitoring.detection_event e
            JOIN monitoring.detected_object o ON e.event_id = o.event_id
            ORDER BY e.timestamp_triggered DESC LIMIT 100;
        """)
        return cur.fetchall()

@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        # 0. Check camera exists
        cur.execute("SELECT 1 FROM monitoring.camera WHERE operational_id = %s", (payload.operational_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Camera with operational_id '{payload.operational_id}' not found")
            
        with db.transaction():
            # 1. Insert into detection_event
            cur.execute("""
                INSERT INTO monitoring.detection_event (event_id, timestamp_triggered, operational_id, confidence_level)
                VALUES ((SELECT COALESCE(MAX(event_id), 0) + 1 FROM monitoring.detection_event), COALESCE(%s, CURRENT_TIMESTAMP), %s, %s)
                RETURNING event_id, timestamp_triggered;
            """, (payload.timestamp, payload.operational_id, payload.confidence_score))
            ev_row = cur.fetchone()
            new_event_id = ev_row["event_id"]
            new_timestamp = ev_row["timestamp_triggered"]

            # 2. Insert into detected_object
            cat = payload.general_category.upper()
            cur.execute("""
                INSERT INTO monitoring.detected_object (object_id, event_id, general_category, dominant_color)
                VALUES ((SELECT COALESCE(MAX(object_id), 0) + 1 FROM monitoring.detected_object), %s, %s, 'unknown')
                RETURNING object_id;
            """, (new_event_id, cat))
            obj_row = cur.fetchone()
            new_object_id = obj_row["object_id"]

            # 3. Optional: insert into person/vehicle based on category
            if cat == 'PERSON':
                cur.execute("INSERT INTO monitoring.person (object_id, baggage_type) VALUES (%s, %s)", (new_object_id, payload.baggage_type))
            elif cat == 'VEHICLE':
                v_type = payload.vehicle_type if payload.vehicle_type else 'Unknown'
                cur.execute("INSERT INTO monitoring.vehicle (object_id, vehicle_type, license_plate) VALUES (%s, %s, %s)", (new_object_id, v_type, payload.license_plate))

            # 4. Optional: insert into object_embedding
            if payload.embedding:
                cur.execute("""
                    INSERT INTO monitoring.object_embedding (object_id, visual_embedding)
                    VALUES (%s, %s::vector)
                """, (new_object_id, str(payload.embedding)))
        
        return {
            "event_id": new_event_id,
            "object_id": new_object_id,
            "operational_id": payload.operational_id,
            "general_category": payload.general_category,
            "confidence_score": payload.confidence_score,
            "timestamp": new_timestamp
        }
