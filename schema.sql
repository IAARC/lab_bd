CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS monitoring;


CREATE TABLE monitoring.camera (
    operational_id VARCHAR(55) NOT NULL,
    device_model VARCHAR(55) NOT NULL,
    has_night_vision BOOLEAN NOT NULL DEFAULT FALSE,
    operating_status VARCHAR(55) NOT NULL DEFAULT 'active',

    CONSTRAINT pk_camera PRIMARY KEY (operational_id),
    CONSTRAINT chk_operating_status CHECK (operating_status IN ('active', 'inactive', 'maintenance', 'fault'))
);

COMMENT ON TABLE monitoring.camera IS 'Registra los dispositivos físicos de captura de video desplegados en las instalaciones.';
COMMENT ON COLUMN monitoring.camera.operational_id IS '- Tipo: VARCHAR(55). Código alfa-numérico institucional único de la cámara (Llave Primaria).';
COMMENT ON COLUMN monitoring.camera.device_model IS '- Tipo: VARCHAR(55). Marca comercial y nombre del modelo del hardware.';
COMMENT ON COLUMN monitoring.camera.has_night_vision IS '- Tipo: BOOLEAN. Flag booleano que indica si el dispositivo soporta captura infrarroja o en entornos oscuros.';
COMMENT ON COLUMN monitoring.camera.operating_status IS '- Tipo: VARCHAR(55). Estado operativo actual de la cámara, restringido por una restricción CHECK.';

CREATE TABLE monitoring.location (
    location_id INT NOT NULL,
    building VARCHAR(255) NOT NULL,
    floor VARCHAR(10) NOT NULL, 
    zone_type VARCHAR(255) NOT NULL,
    operational_id VARCHAR(55) NOT NULL,

    CONSTRAINT pk_location PRIMARY KEY (location_id),
    CONSTRAINT fk_location_camera 
        FOREIGN KEY (operational_id) 
        REFERENCES monitoring.camera(operational_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE monitoring.location IS 'Especifica la ubicación física y espacial de un dispositivo de captura específico.';
COMMENT ON COLUMN monitoring.location.location_id IS '- Tipo: INT. Identificador numérico único para el área espacial (Llave Primaria).';
COMMENT ON COLUMN monitoring.location.building IS '- Tipo: VARCHAR(255). Nombre, bloque o pabellón de la infraestructura.';
COMMENT ON COLUMN monitoring.location.floor IS '- Tipo: INT. Nivel numérico dentro de la distribución del edificio.';
COMMENT ON COLUMN monitoring.location.zone_type IS '- Tipo: VARCHAR(255). Categoría del entorno (Ej: Pasillo, Estacionamiento, Entrada Principal).';
COMMENT ON COLUMN monitoring.location.operational_id IS '- Tipo: VARCHAR(55). La cámara específica asignada a esta ubicación.';


CREATE TABLE monitoring.geographic_coordinates (
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    location_id INT NOT NULL,

    CONSTRAINT pk_geographic_coordinates PRIMARY KEY (latitude, longitude),
    CONSTRAINT fk_coordinates_location 
        FOREIGN KEY (location_id) 
        REFERENCES monitoring.location(location_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE monitoring.geographic_coordinates IS 'Almacena las coordenadas de geolocalización GPS exactas que mapean el punto de control.';
COMMENT ON COLUMN monitoring.geographic_coordinates.latitude IS '- Tipo: FLOAT. Coordenada decimal para la alineación de la latitud.';
COMMENT ON COLUMN monitoring.geographic_coordinates.longitude IS '- Tipo: FLOAT. Coordenada decimal para la alineación de la longitud.';
COMMENT ON COLUMN monitoring.geographic_coordinates.location_id IS '- Tipo: INT. Enlace que establece una relación 1:1 con una ubicación física.';


CREATE TABLE monitoring.detection_event (
    event_id INT NOT NULL,
    timestamp_triggered TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confidence_level NUMERIC(5,4) NOT NULL,
    operational_id VARCHAR(55) NOT NULL,

    CONSTRAINT pk_detection_event PRIMARY KEY (event_id),
    CONSTRAINT fk_event_camera 
        FOREIGN KEY (operational_id) 
        REFERENCES monitoring.camera(operational_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_confidence_level CHECK (confidence_level >= 0.0000 AND confidence_level <= 1.0000)
);

COMMENT ON TABLE monitoring.detection_event IS 'Registra los hitos de inferencia de visión artificial en vivo generados por el pipeline de procesamiento.';
COMMENT ON COLUMN monitoring.detection_event.event_id IS '- Tipo: INT. ID secuencial único para el evento de inferencia del sistema (Llave Primaria).';
COMMENT ON COLUMN monitoring.detection_event.timestamp_triggered IS '- Tipo: TIMESTAMPTZ. Fecha y hora global exacta del suceso con zona horaria.';
COMMENT ON COLUMN monitoring.detection_event.confidence_level IS '- Tipo: NUMERIC(5,4). Tasa de certeza matemática del modelo de IA, acotada estrictamente entre 0.0000 y 1.0000.';
COMMENT ON COLUMN monitoring.detection_event.operational_id IS '- Tipo: VARCHAR(55). Dispositivo de cámara de origen que transmitió el frame analizado.';


CREATE TABLE monitoring.security_alert (
    alert_id INT NOT NULL,
    timestamp_generated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    severity VARCHAR(20) NOT NULL,
    reason_description VARCHAR(524) NOT NULL,
    attendance_status VARCHAR(55) NOT NULL DEFAULT 'unattended',
    event_id INT NOT NULL,

    CONSTRAINT pk_security_alert PRIMARY KEY (alert_id),
    CONSTRAINT fk_alert_event 
        FOREIGN KEY (event_id) 
        REFERENCES monitoring.detection_event(event_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_attendance_status CHECK (attendance_status IN ('unattended', 'in_progress', 'resolved', 'false_alarm'))
);

COMMENT ON TABLE monitoring.security_alert IS 'Despacha notificaciones críticas formales cuando detecciones específicas violan los parámetros de seguridad.';
COMMENT ON COLUMN monitoring.security_alert.alert_id IS '- Tipo: INT. Clave única del registro de la alerta de seguridad (Llave Primaria).';
COMMENT ON COLUMN monitoring.security_alert.timestamp_generated IS '- Tipo: TIMESTAMPTZ. Registro automático en tiempo real del despacho de la emergencia.';
COMMENT ON COLUMN monitoring.security_alert.severity IS '- Tipo: VARCHAR(20). Rango de prioridad de riesgo evaluado por reglas de negocio (low, medium, high, critical).';
COMMENT ON COLUMN monitoring.security_alert.reason_description IS '- Tipo: VARCHAR(524). Texto explicativo y legible por humanos sobre el motivo que disparó la alerta.';
COMMENT ON COLUMN monitoring.security_alert.attendance_status IS '- Tipo: VARCHAR(55). Estado del flujo de trabajo operativo gestionado por el personal de seguridad.';
COMMENT ON COLUMN monitoring.security_alert.event_id IS '- Tipo: INT. Metadatos del evento de visión artificial subyacente que causó la brecha.';


CREATE TABLE monitoring.object_bounding_box (
    coordinate_x INT NOT NULL,
    coordinate_y INT NOT NULL,
    box_height INT NOT NULL,
    box_width INT NOT NULL,
    event_id INT NOT NULL,

    CONSTRAINT pk_object_bounding_box PRIMARY KEY (coordinate_x, coordinate_y, event_id),
    CONSTRAINT fk_bounding_box_event 
        FOREIGN KEY (event_id) 
        REFERENCES monitoring.detection_event(event_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_positive_dimensions CHECK (box_height > 0 AND box_width > 0)
);

COMMENT ON TABLE monitoring.object_bounding_box IS 'Especifica las coordenadas 2D de la caja delimitadora (Bounding Box) del objeto dentro de la matriz del frame.';
COMMENT ON COLUMN monitoring.object_bounding_box.coordinate_x IS '- Tipo: INT. Eje de desplazamiento horizontal en píxeles para el origen del recuadro.';
COMMENT ON COLUMN monitoring.object_bounding_box.coordinate_y IS '- Tipo: INT. Eje de desplazamiento vertical en píxeles para el origen del recuadro.';
COMMENT ON COLUMN monitoring.object_bounding_box.box_height IS '- Tipo: INT. Valor de la altura del recuadro calculada en píxeles.';
COMMENT ON COLUMN monitoring.object_bounding_box.box_width IS '- Tipo: INT. Valor del ancho del recuadro calculada en píxeles.';
COMMENT ON COLUMN monitoring.object_bounding_box.event_id IS '- Tipo: INT. Evento de origen emparejado con estas métricas de diseño específicas.';


CREATE TABLE monitoring.detected_object (
    object_id INT NOT NULL,
    event_id INT NOT NULL,
    general_category VARCHAR(255) NOT NULL,
    dominant_color VARCHAR(50) NOT NULL, 

    CONSTRAINT pk_detected_object PRIMARY KEY (object_id),
    CONSTRAINT fk_object_event 
        FOREIGN KEY (event_id) 
        REFERENCES monitoring.detection_event(event_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_general_category CHECK (general_category IN ('VEHICLE', 'PERSON'))
);

COMMENT ON TABLE monitoring.detected_object IS 'Tabla base abstracta (Súperclase) que aloja los parámetros y atributos generales compartidos por las entidades detectadas.';
COMMENT ON COLUMN monitoring.detected_object.object_id IS '- Tipo: INT. ID único de seguimiento de la entidad objeto en todo el sistema (Llave Primaria).';
COMMENT ON COLUMN monitoring.detected_object.event_id IS '- Tipo: INT. Referencia a la instancia del frame donde la entidad fue rastreada.';
COMMENT ON COLUMN monitoring.detected_object.general_category IS '- Tipo: VARCHAR(255). Campo discriminador que indica el objetivo de herencia estructural.';
COMMENT ON COLUMN monitoring.detected_object.dominant_color IS '- Tipo: VARCHAR(50). Representación normalizada del color. Se unificó en la súperclase y acepta etiquetas de texto plano (ej: Red, White) o códigos Hexadecimales.';


CREATE TABLE monitoring.object_embedding (
    object_id INT NOT NULL,
    visual_embedding vector(512) NOT NULL,

    CONSTRAINT pk_object_embedding PRIMARY KEY (object_id),
    CONSTRAINT fk_embedding_parent 
        FOREIGN KEY (object_id) 
        REFERENCES monitoring.detected_object(object_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE monitoring.object_embedding IS 'Almacenamiento satélite opcional 1:1 que guarda vectores de características de alta dimensión. Evita nulos en la súperclase cuando la confianza es menor al 60%.';
COMMENT ON COLUMN monitoring.object_embedding.object_id IS '- Type: INT. Clave de referencia que coincide con la identidad verificada del objeto padre (Llave Primaria / Llave Foránea).';
COMMENT ON COLUMN monitoring.object_embedding.visual_embedding IS '- Type: vector(512). Arreglo matemático denso que mapea las características visuales extraídas por las capas neuronales.';


CREATE TABLE monitoring.vehicle (
    object_id INT NOT NULL,
    vehicle_type VARCHAR(255) NOT NULL,
    license_plate VARCHAR(20), 

    CONSTRAINT pk_vehicle PRIMARY KEY (object_id),
    CONSTRAINT fk_vehicle_parent 
        FOREIGN KEY (object_id) 
        REFERENCES monitoring.detected_object(object_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE monitoring.vehicle IS 'Subclase especializada que extiende atributos de dominio exclusivos para tránsitos vehiculares.';
COMMENT ON COLUMN monitoring.vehicle.object_id IS '- Tipo: INT. Identidad foránea que refleja el registro abstracto padre (Llave Primaria / Llave Foránea).';
COMMENT ON COLUMN monitoring.vehicle.vehicle_type IS '- Tipo: VARCHAR(255). Tipos de diseño de carrocería (Ej: Sedan, Motorcycle, Truck, SUV).';
COMMENT ON COLUMN monitoring.vehicle.license_plate IS '- Tipo: VARCHAR(20). Cadena opcional de caracteres de la placa de rodaje procesada mediante motores OCR.';


CREATE TABLE monitoring.person (
    object_id INT NOT NULL,
    baggage_type VARCHAR(255),

    CONSTRAINT pk_person PRIMARY KEY (object_id),
    CONSTRAINT fk_person_parent 
        FOREIGN KEY (object_id) 
        REFERENCES monitoring.detected_object(object_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE monitoring.person IS 'Subclase especializada que extiende atributos de dominio exclusivos para el seguimiento de peatones.';
COMMENT ON COLUMN monitoring.person.object_id IS '- Tipo: INT. Identidad foránea que refleja el registro abstracto padre (Llave Primaria / Llave Foránea).';
COMMENT ON COLUMN monitoring.person.baggage_type IS '- Tipo: VARCHAR(255). Clasificación de accesorios o equipajes observados (Ej: Backpack, Suitcase, None).';