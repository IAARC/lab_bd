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
                    cur.execute(
                        """
                        INSERT INTO eventos (id, id_camara, tipo_objeto, confianza, fecha_hora)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE 
                        SET id_camara = EXCLUDED.id_camara,
                            tipo_objeto = EXCLUDED.tipo_objeto,
                            confianza = EXCLUDED.confianza,
                            fecha_hora = EXCLUDED.fecha_hora
                        RETURNING (xmax = 0) AS inserted;
                        """,
                        (
                            int(row["id"]),
                            int(row["id_camara"]),
                            row["tipo_objeto"].strip(),
                            float(row["confianza"]),
                            row["fecha_hora"].strip()
                        )
                    )
                    res = cur.fetchone()
                    if res and res["inserted"]:
                        agregadas += 1
                    else:
                        actualizadas += 1
            except Exception:
                errores += 1

        db.commit()

    return {
        "filas_agregadas": agregadas,
        "filas_actualizadas": actualizadas,
        "filas_no_subidas": errores
    }