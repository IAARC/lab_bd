# Informe Corte 3 — VISIÓN-DB
## 1. Funciones Analíticas (Entregable 3A)

### `get_camera_traffic(camara_id, fecha_inicio, fecha_fin)`
Retorna el conteo de detecciones por hora del día para una cámara y rango de fechas dado. Usa `EXTRACT(HOUR FROM timestamp_triggered)` agrupando por hora, casteado a `INT` para mayor claridad semántica (una hora del día es un entero 0-23, no un valor decimal).

### `get_zone_summary(tipo_zona)`
Para cada ubicación del tipo de zona indicado, retorna el número de cámaras activas, el total de eventos y el total de alertas críticas. Usa `LEFT JOIN` desde `location` hacia `camera`, `detection_event` y `security_alert`, con `COUNT(DISTINCT ...) FILTER (WHERE ...)` para los conteos condicionados por estado/severidad.

**Nota de diseño:** como una ubicación puede tener varias cámaras (ver sección 3), `camaras_activas` ahora puede ser 0, 1 o más por ubicación — antes, con el esquema de Corte 2, el máximo posible era 1.

### `find_similar_objects(ref_id, threshold, max_results)`
Recupera el embedding del objeto de referencia y busca objetos del mismo tipo (`general_category`) cuya distancia coseno (`<=>`, pgvector) sea menor o igual al umbral. Excluye el propio objeto de referencia y retorna el nombre de la cámara de origen (`camera_name`), no su ID, conforme al enunciado.

## 2. Triggers (Entregable 3B)

### `trg_alerta_zona_peatonal`
Se dispara `AFTER INSERT` en `detected_object`. Si el objeto insertado es `VEHICLE` y la ubicación de la cámara que generó el evento es de zona `peatonal_restringida`, inserta automáticamente una alerta con severidad `high` en `security_alert`.

**Decisión de diseño:** el enunciado especifica el trigger en `EVENTO_DETECCION` (`detection_event`), pero `general_category` solo existe en `detected_object`. Se optó por disparar el trigger en `detected_object`, ya que es ahí donde se conoce el tipo de objeto sin necesidad de un `SELECT` adicional dentro de la función.

### `trg_audit_camara`
Se dispara `AFTER UPDATE` en `camera`. Si `operating_status` cambia a `inactive`, inserta un registro en `camera_audit` con el `operational_id`, la fecha del cambio y el estado anterior (`OLD.operating_status`).

## 3. Cambio en la Foreign Key: `location` ↔ `camera`

En el Corte 2, la FK estaba en `location.operational_id → camera.operational_id`, lo que forzaba una relación de **1 ubicación → 1 cámara**.

Al construir el seed con datos reales se identificó que varias ubicaciones (ej. *"Edificio A - Entrada Principal"*) tienen **más de una cámara** instalada — un caso de negocio perfectamente válido que el modelo anterior no podía representar.

**Corrección:** se invirtió la FK a `camera.location_id → location.location_id`, habilitando **1 ubicación → N cámaras**. Esto requirió:
- Quitar `operational_id` de `location` y agregar `location_id` a `camera`.
- Reordenar la creación de tablas (`location` ahora se crea antes de `camera`).
- Actualizar los `JOIN` en `get_zone_summary` y en `fn_alerta_zona_peatonal`, que antes navegaban `location → camera` directamente y ahora navegan `camera → location`.

## 4. Nueva columna: `camera.camera_name`

En el Corte 2 la tabla `camera` solo tenía `operational_id` (código alfa-numérico institucional, ej. `CAM-A-ENT-01`) como identificador.

El enunciado de `find_similar_objects` pide retornar el **nombre** de la cámara donde fue detectado el objeto, no su código operativo. Por eso se agregó `camera_name VARCHAR(100)` a la tabla `camera`, usado en los reportes y consultas analíticas en lugar de exponer directamente el `operational_id` como identificador legible.

## 5. Seed de datos

Se generó un script (`generate_seed.py`) que transforma el CSV desnormalizado (`seed_100.csv`, 100 filas) en sentencias `INSERT` para todas las tablas, deduplicando `location` y `camera`, separando eventos con múltiples objetos detectados, y mapeando valores en español del CSV a los valores en inglés usados por las restricciones `CHECK` del esquema. También sincroniza la secuencia `security_alert_id_seq` al final de la carga para evitar colisiones con los triggers en inserciones posteriores.

**Orden de carga recomendado:** `schema.sql` → `functions.sql` → `seed.sql` → `triggers.sql` (los triggers se cargan al final para que no se disparen durante la carga histórica del seed).

## 6. Reemplazo del script generador de seed

La primera versión del script (basado en `csv.DictReader` con sets de control por tabla) se reemplazó por `generate_seed.py` (basado en `pandas`/listas estructuradas) por las siguientes razones:

- **`location_id` no determinístico:** la versión anterior generaba el identificador de ubicación con `hash(f"{lat},{lon},{bldg}") % 100000`. El `hash()` de Python para strings no es estable entre ejecuciones del intérprete (varía por el `PYTHONHASHSEED` de cada proceso), por lo que el mismo CSV podía producir distintos `location_id` en cada corrida, además de riesgo de colisión por el módulo. El script actual asigna IDs secuenciales (1, 2, 3...) en el orden de primera aparición, siempre reproducibles.
- **FK location → camera obsoleta:** el script anterior insertaba `location.operational_id = c_id`, dependiente del esquema del Corte 2 donde una ubicación solo podía tener una cámara. Tras invertir la FK (sección 3), el script actual asigna `camera.location_id` y ya no necesita ese campo en `location`.
- **Color de vehículo perdido:** `dominant_color` se completaba siempre con `persona_color_ropa`, sin contemplar `vehiculo_color`. Para todo objeto `VEHICLE`, el color principal quedaba en `NULL`. El script actual selecciona la columna de color correcta según `objeto_tipo`.
- **`license_plate` siempre `NULL`:** el `INSERT` de `vehicle` fijaba la matrícula como `NULL` de forma fija en el código, ignorando la columna `vehiculo_matricula` del CSV. El script actual la usa directamente.
- **Sin `security_alert`:** el script anterior no generaba ninguna fila de alerta, a pesar de que el CSV trae 10 casos de vehículo en zona `peatonal_restringida`. El script actual mapea `alerta_severidad`/`alerta_estado` del español al inglés y genera el `INSERT` correspondiente, sincronizando además `security_alert_id_seq` al final de la carga.
- **`ON CONFLICT DO NOTHING` generalizado:** silenciaba errores de llave duplicada en todas las tablas, lo cual puede esconder bugs de generación (como el de `location_id`) en lugar de hacerlos evidentes durante las pruebas. El script actual no satura el `INSERT` con esa cláusula; cualquier colisión de llave se ve como un error real al cargar.

En conjunto, estos defectos no rompían la ejecución del script (no lanzaban excepciones), pero producían un seed silenciosamente incompleto o incorrecto: vehículos sin color ni matrícula, cero alertas, y ubicaciones potencialmente duplicadas o inconsistentes entre corridas.

