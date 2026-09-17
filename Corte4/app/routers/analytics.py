from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from psycopg import Connection
from app.database import get_db
from app.schemas.analytics import CameraTrafficOut, ZoneSummaryOut, AlertsSummaryOut

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/cameras/{operational_id}/traffic", response_model=CameraTrafficOut)
def get_camera_traffic_endpoint(
    operational_id: str,
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Connection = Depends(get_db)
):
    with db.cursor() as cur:
        # Invoca la función almacenada get_camera_traffic
        cur.execute("SELECT * FROM monitoring.get_camera_traffic(%s, %s, %s);", (operational_id, from_date, to_date))
        rows = cur.fetchall()
        return {"operational_id": operational_id, "from_date": from_date, "to_date": to_date, "traffic": rows}

@router.get("/zones/{zone_type}", response_model=ZoneSummaryOut)
def get_zone_summary_endpoint(zone_type: str, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM monitoring.get_zone_summary(%s);", (zone_type,))
        result = cur.fetchall()
        return {"zone_type": zone_type, "summary": result}

@router.get("/alerts/summary", response_model=AlertsSummaryOut)
def get_alerts_summary(days: int = Query(30, ge=1), db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        query = """
            SELECT 
                c.operational_id,
                a.severity,
                COUNT(a.alert_id) AS total_alerts
            FROM monitoring.security_alert a
            JOIN monitoring.detection_event e ON a.event_id = e.event_id
            JOIN monitoring.camera c ON c.operational_id = e.operational_id
            WHERE a.timestamp_generated >= CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
            GROUP BY c.operational_id, a.severity
            ORDER BY c.operational_id, a.severity;
        """
        cur.execute(query, (days,))
        rows = cur.fetchall()
        return {"days_analyzed": days, "data": rows}