import sys
import csv
import ast
from datetime import datetime

CAMERA_STATUS_MAP = {
    "activa": "active",
    "inactiva": "inactive",
    "en_mantenimiento": "maintenance",
    "falla": "fault",
}

OBJECT_CATEGORY_MAP = {
    "persona": "PERSON",
    "vehiculo": "VEHICLE",
}

ALERT_SEVERITY_MAP = {
    "baja": "low",
    "media": "medium",
    "alta": "high",
    "critica": "critical",
}

ALERT_STATUS_MAP = {
    "pendiente": "unattended",
    "en_progreso": "in_progress",
    "atendida": "resolved",
    "descartada": "false_alarm",
}

CONFIDENCE_THRESHOLD_FOR_EMBEDDING = 0.60

def sql_str(value):
    if value is None or value == "":
        return "NULL"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def sql_bool(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None or value == "":
        return "NULL"
    return "TRUE" if str(value).strip().lower() == "true" else "FALSE"


def sql_num(value):
    """Convierte un valor numeico a literal SQL, o NULL si esta vacio."""
    if value is None or value == "":
        return "NULL"
    return str(value)


def parse_embedding(raw):
    if raw is None or raw.strip() == "":
        return None
    values = ast.literal_eval(raw)
    if len(values) != 512:
        raise ValueError(f"Embedding con {len(values)} dimensiones, se esperaban 512.")
    return "[" + ",".join(str(v) for v in values) + "]"


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 generate_seed.py <archivo_entrada.csv> <archivo_salida.sql>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

  
    locations = {}  # ubicacion_nombre -> location_id
    location_rows = []  # (location_id, building, floor, zone_type)
    coordinate_rows = []  # (latitude, longitude, location_id)

    next_location_id = 1
    for row in rows:
        nombre = row["ubicacion_nombre"]
        if nombre not in locations:
            locations[nombre] = next_location_id
            location_rows.append((
                next_location_id,
                nombre,
                row["ubicacion_piso"],
                row["ubicacion_tipo_zona"],
            ))
            coordinate_rows.append((
                row["ubicacion_latitud"],
                row["ubicacion_longitud"],
                next_location_id,
            ))
            next_location_id += 1

   
    cameras = {}  # camara_nombre -> True (ya insertada)
    camera_rows = []  # (operational_id, device_model, has_night_vision, operating_status, camera_name, location_id)

    for row in rows:
        cam_id = row["camara_nombre"]
        if cam_id not in cameras:
            cameras[cam_id] = True
            location_id = locations[row["ubicacion_nombre"]]
            estado = CAMERA_STATUS_MAP[row["camara_estado"]]
            camera_rows.append((
                cam_id,
                row["camara_modelo"],
                row["camara_vision_nocturna"],
                estado,
                cam_id,  # camera_name: usamos el mismo codigo legible como nombre
                location_id,
            ))

 
    events_seen = set()
    event_rows = []          # (event_id, timestamp, confidence, operational_id)
    bbox_rows = []            # (x, y, h, w, event_id)

    for row in rows:
        eid = int(row["evento_id"])
        if eid not in events_seen:
            events_seen.add(eid)
            event_rows.append((
                eid,
                row["evento_marca_tiempo"],
                row["evento_confianza"],
                row["camara_nombre"],
            ))
            bbox_rows.append((
                row["evento_bbox_x"],
                row["evento_bbox_y"],
                row["evento_bbox_h"],
                row["evento_bbox_w"],
                eid,
            ))

  
    detected_object_rows = []  # (object_id, event_id, general_category, dominant_color)
    vehicle_rows = []          # (object_id, vehicle_type, license_plate)
    person_rows = []           # (object_id, baggage_type)
    embedding_rows = []        # (object_id, visual_embedding_literal)
    alert_rows = []            # (alert_id, timestamp, severity, description, status, event_id)

    next_object_id = 1
    next_alert_id = 1

    for row in rows:
        eid = int(row["evento_id"])
        tipo = row["objeto_tipo"]
        category = OBJECT_CATEGORY_MAP[tipo]
        object_id = next_object_id
        next_object_id += 1

        if tipo == "persona":
            dominant_color = row["persona_color_ropa"]
        else:
            dominant_color = row["vehiculo_color"]

        detected_object_rows.append((object_id, eid, category, dominant_color))

        if tipo == "persona":
            baggage = row["persona_porta_equipaje"]
            # CSV trae True/False (string) o vacio
            if baggage is None or baggage == "":
                baggage_label = None
            else:
                baggage_label = "Backpack" if str(baggage).strip().lower() == "true" else "None"
            person_rows.append((object_id, baggage_label))
        else:
            vehicle_rows.append((object_id, row["vehiculo_tipo"], row["vehiculo_matricula"]))

        embedding_literal = parse_embedding(row["objeto_embedding"])
        confidence = float(row["evento_confianza"])
        if embedding_literal is not None:
            embedding_rows.append((object_id, embedding_literal))
        # Validacion cruzada con la regla de negocio (confianza >= 60% -> embedding)
        elif confidence >= CONFIDENCE_THRESHOLD_FOR_EMBEDDING:
            print(f"[WARN] event_id={eid} obj#{object_id} confianza={confidence} "
                  f">= 0.60 pero no tiene embedding en el CSV.")

        severity_raw = row["alerta_severidad"]
        if severity_raw:
            alert_rows.append((
                next_alert_id,
                row["evento_marca_tiempo"],
                ALERT_SEVERITY_MAP[severity_raw],
                row["alerta_descripcion"],
                ALERT_STATUS_MAP[row["alerta_estado"]],
                eid,
            ))
            next_alert_id += 1

   
    lines = []
    lines.append("-- ============================================================================")
    lines.append("-- SEED DATA: Security Detection and Alert System (monitoring schema)")
    lines.append(f"-- Generado automaticamente a partir de seed_100.csv ({len(rows)} filas de origen)")
    lines.append("-- ============================================================================")
    lines.append("")
    lines.append("BEGIN;")
    lines.append("")

    # location
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- location")
    lines.append("-- ----------------------------------------------------------------------------")
    for loc_id, building, floor, zone_type in location_rows:
        lines.append(
            "INSERT INTO monitoring.location (location_id, building, floor, zone_type) "
            f"VALUES ({loc_id}, {sql_str(building)}, {sql_str(floor)}, {sql_str(zone_type)});"
        )
    lines.append("")

    # camera
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- camera")
    lines.append("-- ----------------------------------------------------------------------------")
    for op_id, model, night_vision, status, cam_name, loc_id in camera_rows:
        lines.append(
            "INSERT INTO monitoring.camera "
            "(operational_id, device_model, has_night_vision, operating_status, camera_name, location_id) "
            f"VALUES ({sql_str(op_id)}, {sql_str(model)}, {sql_bool(night_vision)}, "
            f"{sql_str(status)}, {sql_str(cam_name)}, {loc_id});"
        )
    lines.append("")

    # geographic_coordinates
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- geographic_coordinates")
    lines.append("-- ----------------------------------------------------------------------------")
    for lat, lon, loc_id in coordinate_rows:
        lines.append(
            "INSERT INTO monitoring.geographic_coordinates (latitude, longitude, location_id) "
            f"VALUES ({sql_num(lat)}, {sql_num(lon)}, {loc_id});"
        )
    lines.append("")

    # detection_event
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- detection_event")
    lines.append("-- ----------------------------------------------------------------------------")
    for eid, ts, confidence, op_id in event_rows:
        lines.append(
            "INSERT INTO monitoring.detection_event "
            "(event_id, timestamp_triggered, confidence_level, operational_id) "
            f"VALUES ({eid}, {sql_str(ts)}, {sql_num(confidence)}, {sql_str(op_id)});"
        )
    lines.append("")

    # object_bounding_box
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- object_bounding_box")
    lines.append("-- ----------------------------------------------------------------------------")
    for x, y, h, w, eid in bbox_rows:
        lines.append(
            "INSERT INTO monitoring.object_bounding_box "
            "(coordinate_x, coordinate_y, box_height, box_width, event_id) "
            f"VALUES ({sql_num(x)}, {sql_num(y)}, {sql_num(h)}, {sql_num(w)}, {eid});"
        )
    lines.append("")

    # detected_object
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- detected_object")
    lines.append("-- ----------------------------------------------------------------------------")
    for obj_id, eid, category, color in detected_object_rows:
        lines.append(
            "INSERT INTO monitoring.detected_object "
            "(object_id, event_id, general_category, dominant_color) "
            f"VALUES ({obj_id}, {eid}, {sql_str(category)}, {sql_str(color)});"
        )
    lines.append("")

    # vehicle
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- vehicle")
    lines.append("-- ----------------------------------------------------------------------------")
    for obj_id, vtype, plate in vehicle_rows:
        lines.append(
            "INSERT INTO monitoring.vehicle (object_id, vehicle_type, license_plate) "
            f"VALUES ({obj_id}, {sql_str(vtype)}, {sql_str(plate)});"
        )
    lines.append("")

    # person
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- person")
    lines.append("-- ----------------------------------------------------------------------------")
    for obj_id, baggage in person_rows:
        lines.append(
            "INSERT INTO monitoring.person (object_id, baggage_type) "
            f"VALUES ({obj_id}, {sql_str(baggage)});"
        )
    lines.append("")

    # object_embedding
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- object_embedding (solo objetos con confidence_level >= 0.60)")
    lines.append("-- ----------------------------------------------------------------------------")
    for obj_id, emb_literal in embedding_rows:
        lines.append(
            "INSERT INTO monitoring.object_embedding (object_id, visual_embedding) "
            f"VALUES ({obj_id}, '{emb_literal}');"
        )
    lines.append("")

    # security_alert
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- security_alert")
    lines.append("-- ----------------------------------------------------------------------------")
    for alert_id, ts, severity, description, status, eid in alert_rows:
        lines.append(
            "INSERT INTO monitoring.security_alert "
            "(alert_id, timestamp_generated, severity, reason_description, attendance_status, event_id) "
            f"VALUES ({alert_id}, {sql_str(ts)}, {sql_str(severity)}, "
            f"{sql_str(description)}, {sql_str(status)}, {eid});"
        )
    lines.append("")

    # Sincronizar secuencias usadas por los triggers/funciones con el ultimo id insertado
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("-- Sincronizar la secuencia de alertas para que los triggers no colisionen")
    lines.append("-- con los alert_id ya insertados por este seed")
    lines.append("-- ----------------------------------------------------------------------------")
    lines.append("SELECT setval('monitoring.security_alert_id_seq', "
                  f"{max(next_alert_id - 1, 1)}, true);")
    lines.append("")

    lines.append("COMMIT;")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"OK: {output_path} generado con:")
    print(f"  - {len(location_rows)} locations")
    print(f"  - {len(camera_rows)} cameras")
    print(f"  - {len(coordinate_rows)} geographic_coordinates")
    print(f"  - {len(event_rows)} detection_events")
    print(f"  - {len(bbox_rows)} object_bounding_box")
    print(f"  - {len(detected_object_rows)} detected_object")
    print(f"  - {len(vehicle_rows)} vehicle")
    print(f"  - {len(person_rows)} person")
    print(f"  - {len(embedding_rows)} object_embedding")
    print(f"  - {len(alert_rows)} security_alert")


if __name__ == "__main__":
    main()
