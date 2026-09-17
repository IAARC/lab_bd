# app/routers/extra_csv.py
import csv
import io
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from psycopg import Connection
from app.database import get_db

router = APIRouter(tags=["Ingesta Masiva"])

@router.post("/csv")
async def upload_csv_data(file: UploadFile = File(...), db: Connection = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .csv")

    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))

    agregadas = 0
    actualizadas = 0
    errores = 0

    with db.cursor() as cur:
        for row in reader:
            try:
                # Subtransacción por fila (savepoint) para que un error no aborte todo el lote
                with db.transaction():
                    # Upsert detection_event
                    cur.execute(
                        """
                        INSERT INTO monitoring.detection_event (event_id, operational_id, timestamp_triggered, confidence_level)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (event_id) DO UPDATE 
                        SET operational_id = EXCLUDED.operational_id,
                            timestamp_triggered = EXCLUDED.timestamp_triggered,
                            confidence_level = EXCLUDED.confidence_level
                        RETURNING (xmax = 0) AS inserted;
                        """,
                        (
                            int(row["event_id"]),
                            row["operational_id"],
                            row["timestamp"] if "timestamp" in row and row["timestamp"] else None,
                            float(row["confidence_score"])
                        )
                    )
                    res_event = cur.fetchone()
                    
                    # Upsert detected_object
                    cur.execute(
                        """
                        INSERT INTO monitoring.detected_object (object_id, event_id, general_category, dominant_color)
                        VALUES ((SELECT COALESCE(MAX(object_id), 0) + 1 FROM monitoring.detected_object), %s, %s, 'unknown')
                        """,
                        (int(row["event_id"]), 'PERSON')
                    )

                    if res_event and res_event["inserted"]:
                        agregadas += 1
                    else:
                        actualizadas += 1
            except Exception as e:
                print("Error on row:", row, e)
                errores += 1

        db.commit()

    return {
        "filas_agregadas": agregadas,
        "filas_actualizadas": actualizadas,
        "filas_no_subidas": errores
    }