CREATE OR REPLACE FUNCTION monitoring.fn_alerta_zona_peatonal()
RETURNS TRIGGER AS $$
DECLARE
    v_zone_type VARCHAR(255);
    v_alert_id INT;
BEGIN
    SELECT l.zone_type INTO v_zone_type
    FROM monitoring.detection_event de
    JOIN monitoring.camera c ON de.operational_id = c.operational_id
    JOIN monitoring.location l ON c.location_id = l.location_id
    WHERE de.event_id = NEW.event_id;

    --- Si el objeto detectado es un vehículo y la zona es peatonal_restringida
    IF NEW.general_category = 'VEHICLE' AND v_zone_type = 'peatonal_restringida' THEN
        
        --- Obtener el siguiente valor de la secuencia para evitar colisiones de llaves primarias
        v_alert_id := NEXTVAL('monitoring.security_alert_id_seq');

        INSERT INTO monitoring.security_alert (
            alert_id,
            timestamp_generated,
            severity,
            reason_description,
            attendance_status,
            event_id
        ) VALUES (
            v_alert_id,
            CURRENT_TIMESTAMP,
            'high',
            'ALERTA AUTOMÁTICA: Intrusión vehicular detectada en paso peatonal restringido.',
            'unattended',
            NEW.event_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE TRIGGER trg_alerta_zona_peatonal
AFTER INSERT ON monitoring.detected_object
FOR EACH ROW
EXECUTE FUNCTION monitoring.fn_alerta_zona_peatonal();


CREATE OR REPLACE FUNCTION monitoring.fn_audit_camara()
RETURNS TRIGGER AS $$
BEGIN
    --- Se activa únicamente si el estado de la cámara cambia al valor 'inactive'
    IF NEW.operating_status = 'inactive' AND OLD.operating_status IS DISTINCT FROM 'inactive' THEN
        INSERT INTO monitoring.camera_audit (
            operational_id,
            change_timestamp,
            previous_status
        ) VALUES (
            NEW.operational_id,
            CURRENT_TIMESTAMP,
            OLD.operating_status
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_audit_camara
AFTER UPDATE ON monitoring.camera
FOR EACH ROW
EXECUTE FUNCTION monitoring.fn_audit_camara();