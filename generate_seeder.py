import csv
import os

ARCHIVO_CSV = "seed_100.csv"  
ARCHIVO_SQL_SALIDA = "seed.sql"

def procesar_campo_texto(valor):
    if not valor or str(valor).strip().upper() == "NULL" or str(valor).strip() == "":
        return "NULL"
    valor_escapado = str(valor).strip().replace("'", "''")
    return f"'{valor_escapado}'"

def procesar_campo_numero(valor):
    if not valor or str(valor).strip().upper() == "NULL" or str(valor).strip() == "":
        return "NULL"
    return str(valor).strip()

def procesar_campo_booleano(valor):
    if not valor or str(valor).strip().upper() == "NULL" or str(valor).strip() == "":
        return "FALSE"
    val = str(valor).strip().upper()
    if val in ["TRUE", "1", "YES", "SI", "T"]:
        return "TRUE"
    return "FALSE"

def mapear_estado_camara(valor):
    val = str(valor).strip().lower()
    if val in ["activa", "activo", "active"]:
        return "'active'"
    elif val in ["inactiva", "inactivo", "inactive"]:
        return "'inactive'"
    elif val in ["mantenimiento", "maintenance"]:
        return "'maintenance'"
    elif val in ["falla", "error", "fault"]:
        return "'fault'"
    return "'active'" 

def generar_seed():
    if not os.path.exists(ARCHIVO_CSV):
        print(f"Error: No se encontró el archivo {ARCHIVO_CSV}")
        return

    camaras_procesadas = set()
    ubicaciones_procesadas = set()
    coordenadas_procesadas = set()
    eventos_procesados = set()
    recuadros_procesados = set()
    objetos_procesados = set()
    vehiculos_procesados = set()
    personas_procesadas = set()

    sql_cameras = ["\n-- Poblado de TABLE: camera\n"]
    sql_locations = ["\n-- Poblado de TABLE: location\n"]
    sql_coordinates = ["\n-- Poblado de TABLE: geographic_coordinates\n"]
    sql_events = ["\n-- Poblado de TABLE: detection_event\n"]
    sql_boxes = ["\n-- Poblado de TABLE: object_bounding_box\n"]
    sql_objects = ["\n-- Poblado de TABLE: detected_object\n"]
    sql_vehicles = ["\n-- Poblado de TABLE: vehicle\n"]
    sql_people = ["\n-- Poblado de TABLE: person\n"]


    with open(ARCHIVO_CSV, mode="r", encoding="utf-8-sig") as f:
        primera_linea = f.readline()
        if ";" in primera_linea: separador = ";"
        elif "," in primera_linea: separador = ","
        else: separador = "\t" 
        
        f.seek(0)
        lector = csv.DictReader(f, delimiter=separador)
        if lector.fieldnames:
            lector.fieldnames = [name.strip() for name in lector.fieldnames]
        
        for num_fila, fila in enumerate(lector, start=1):
            try:
                fila = {k: (v.strip() if v else "") for k, v in fila.items() if k is not None}
                
                c_id = fila.get("camara_nombre", "").strip()
                if not c_id: continue 
                    
                if c_id not in camaras_procesadas:
                    model = procesar_campo_texto(fila.get("camara_modelo"))
                    night = procesar_campo_booleano(fila.get("camara_vision_nocturna"))
                    status = mapear_estado_camara(fila.get("camara_estado", "active"))
                    sql_cameras.append(f"INSERT INTO monitoring.camera (operational_id, device_model, has_night_vision, operating_status) VALUES ('{c_id}', {model}, {night}, {status}) ON CONFLICT DO NOTHING;\n")
                    camaras_procesadas.add(c_id)

                lat = fila.get("ubicacion_latitud", "").strip()
                lon = fila.get("ubicacion_longitud", "").strip()
                bldg_raw = fila.get("ubicacion_nombre", "Desconocido")
                l_id = str(abs(hash(f"{lat},{lon},{bldg_raw}")) % 100000)
                
                if l_id not in ubicaciones_procesadas:
                    bldg = procesar_campo_texto(bldg_raw)
                    floor = procesar_campo_texto(fila.get("ubicacion_piso"))
                    z_type = procesar_campo_texto(fila.get("ubicacion_tipo_zona"))
                    sql_locations.append(f"INSERT INTO monitoring.location (location_id, building, floor, zone_type, operational_id) VALUES ({l_id}, {bldg}, {floor}, {z_type}, '{c_id}') ON CONFLICT DO NOTHING;\n")
                    ubicaciones_procesadas.add(l_id)

                coord_key = f"{lat},{lon}"
                if lat and lon and coord_key not in coordenadas_procesadas:
                    sql_coordinates.append(f"INSERT INTO monitoring.geographic_coordinates (latitude, longitude, location_id) VALUES ({lat}, {lon}, {l_id}) ON CONFLICT DO NOTHING;\n")
                    coordenadas_procesadas.add(coord_key)

                e_id = fila.get("evento_id", "").strip()
                if e_id and e_id not in eventos_procesados:
                    ts = procesar_campo_texto(fila.get("evento_marca_tiempo"))
                    conf = procesar_campo_numero(fila.get("evento_confianza"))
                    sql_events.append(f"INSERT INTO monitoring.detection_event (event_id, timestamp_triggered, confidence_level, operational_id) VALUES ({e_id}, {ts}, {conf}, '{c_id}') ON CONFLICT DO NOTHING;\n")
                    eventos_procesados.add(e_id)

                bx = fila.get("evento_bbox_x", "").strip()
                by = fila.get("evento_bbox_y", "").strip()
                box_key = f"{bx},{by},{e_id}"
                if e_id and bx and by and box_key not in recuadros_procesados:
                    bw = procesar_campo_numero(fila.get("evento_bbox_w"))
                    bh = procesar_campo_numero(fila.get("evento_bbox_h"))
                    sql_boxes.append(f"INSERT INTO monitoring.object_bounding_box (coordinate_x, coordinate_y, box_height, box_width, event_id) VALUES ({bx}, {by}, {bh}, {bw}, {e_id}) ON CONFLICT DO NOTHING;\n")
                    recuadros_procesados.add(box_key)

                o_id = str(num_fila) 
                if e_id and o_id not in objetos_procesados:
                    cat = fila.get("objeto_tipo", "").strip().upper()
                    if cat == "PERSONA": cat_sql = "PERSON"
                    elif cat == "VEHICULO": cat_sql = "VEHICLE"
                    else: cat_sql = cat
                        
                    color_sql = procesar_campo_texto(fila.get("persona_color_ropa"))

                    sql_objects.append(f"INSERT INTO monitoring.detected_object (object_id, event_id, general_category, dominant_color) VALUES ({o_id}, {e_id}, '{cat_sql}', {color_sql}) ON CONFLICT DO NOTHING;\n")
                    objetos_procesados.add(o_id)

                    if cat_sql == "VEHICLE" and o_id not in vehiculos_procesados:
                        v_type = procesar_campo_texto(fila.get("vehiculo_tipo"))
                        sql_vehicles.append(f"INSERT INTO monitoring.vehicle (object_id, vehicle_type, license_plate) VALUES ({o_id}, {v_type}, NULL) ON CONFLICT DO NOTHING;\n")
                        vehiculos_procesados.add(o_id)
                    elif cat_sql == "PERSON" and o_id not in personas_procesadas:
                        porta = fila.get("persona_porta_equipaje", "")
                        bag = "Backpack" if str(porta).strip().upper() in ["TRUE", "1", "YES", "SI", "T"] else "None"
                        sql_people.append(f"INSERT INTO monitoring.person (object_id, baggage_type) VALUES ({o_id}, '{bag}') ON CONFLICT DO NOTHING;\n")
                        personas_procesadas.add(o_id)

            except Exception as e:
                print(f"Error procesando la fila {num_fila}: {str(e)}")
                continue

    with open(ARCHIVO_SQL_SALIDA, "w", encoding="utf-8") as f_out:
        f_out.write("-- ============================================================================\n")
        f_out.write("-- SCRIPT DML SEEDER GENERADO AUTOMÁTICAMENTE\n")
        f_out.write("-- ============================================================================\n\n")
        f_out.write("BEGIN;\n")
        f_out.writelines(sql_cameras)
        f_out.writelines(sql_locations)
        f_out.writelines(sql_coordinates)
        f_out.writelines(sql_events)
        f_out.writelines(sql_boxes)
        f_out.writelines(sql_objects)
        f_out.writelines(sql_vehicles)
        f_out.writelines(sql_people)
        f_out.write("\nCOMMIT;\n")

    print(f"Archivo generado con éxito.")

if __name__ == "__main__":
    generar_seed()