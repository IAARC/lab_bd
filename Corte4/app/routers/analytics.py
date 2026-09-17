from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from psycopg import Connection
from app.database import get_db
from app.schemas.analytics import CameraTrafficOut, ZoneSummaryOut, AlertsSummaryOut

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/cameras/{id}/traffic", response_model=CameraTrafficOut)
def get_camera_traffic_endpoint(
    id: int,
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: Connection = Depends(get_db)
):
    with db.cursor() as cur:
        # Invoca la función almacenada get_camera_traffic
        cur.execute("SELECT * FROM get_camera_traffic(%s, %s, %s);", (id, from_date, to_date))
        rows = cur.fetchall()
        return {"camera_id": id, "from": from_date, "to": to_date, "traffic": rows}

@router.get("/zones/{tipo}", response_model=ZoneSummaryOut)
def get_zone_summary_endpoint(tipo: str, db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM get_zone_summary(%s);", (tipo,))
        result = cur.fetchall()
        return {"tipo_zona": tipo, "summary": result}

@router.get("/alerts/summary", response_model=AlertsSummaryOut)
def get_alerts_summary(days: int = Query(30, ge=1), db: Connection = Depends(get_db)):
    with db.cursor() as cur:
        query = """
            SELECT 
                a.id_camara,
                c.codigo AS camara_codigo,
                a.severidad,
                COUNT(a.id) AS total_alertas
            FROM alertas a
            JOIN camaras c ON c.id = a.id_camara
            WHERE a.fecha_hora >= CURRENT_TIMESTAMP - (%s || ' days')::INTERVAL
            GROUP BY a.id_camara, c.codigo, a.severidad
            ORDER BY a.id_camara, a.severidad;
        """
        cur.execute(query, (days,))
        rows = cur.fetchall()
        return {"days_analyzed": days, "data": rows}