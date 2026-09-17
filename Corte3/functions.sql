
DROP FUNCTION IF EXISTS monitoring.get_camera_traffic(VARCHAR, DATE, DATE);

CREATE OR REPLACE FUNCTION monitoring.get_camera_traffic(
    p_camara_id VARCHAR(55), --- Se usa VARCHAR(55) para coincidir con operational_id
    p_fecha_inicio DATE,
    p_fecha_fin DATE
)
RETURNS TABLE (
    hora_dia INT,
    conteo_detecciones BIGINT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        EXTRACT(HOUR FROM timestamp_triggered)::INT AS hora_dia,
        COUNT(*) AS conteo_detecciones
    FROM 
        monitoring.detection_event
    WHERE 
        operational_id = p_camara_id
        AND timestamp_triggered::DATE >= p_fecha_inicio
        AND timestamp_triggered::DATE <= p_fecha_fin
    GROUP BY 
        EXTRACT(HOUR FROM timestamp_triggered)
    ORDER BY 
        hora_dia;
END;
$$;



DROP FUNCTION IF EXISTS monitoring.get_zone_summary(VARCHAR);

CREATE OR REPLACE FUNCTION monitoring.get_zone_summary(
    p_tipo_zona VARCHAR
)
RETURNS TABLE (
    id_ubicacion INT,
    camaras_activas BIGINT,
    total_eventos BIGINT,
    total_alertas_criticas BIGINT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.location_id AS id_ubicacion,
        COUNT(DISTINCT c.operational_id) FILTER (WHERE c.operating_status = 'active') AS camaras_activas,
        COUNT(DISTINCT de.event_id) AS total_eventos,
        COUNT(DISTINCT sa.alert_id) FILTER (WHERE sa.severity = 'critical') AS total_alertas_criticas
    FROM 
        monitoring.location l
    LEFT JOIN 
        monitoring.camera c ON c.location_id = l.location_id
    LEFT JOIN 
        monitoring.detection_event de ON c.operational_id = de.operational_id
    LEFT JOIN 
        monitoring.security_alert sa ON de.event_id = sa.event_id
    WHERE 
        l.zone_type = p_tipo_zona
    GROUP BY 
        l.location_id
    ORDER BY 
        l.location_id;
END;
$$;


DROP FUNCTION IF EXISTS monitoring.find_similar_objects(INT, FLOAT, INT);

CREATE OR REPLACE FUNCTION monitoring.find_similar_objects(
    p_ref_id INT,
    p_threshold FLOAT,
    p_max_results INT
)
RETURNS TABLE (
    objeto_encontrado_id INT,
    tipo VARCHAR,
    distancia_coseno FLOAT,
    camara_origen VARCHAR(100),
    fecha_evento TIMESTAMPTZ
) 
LANGUAGE plpgsql
AS $$
DECLARE
    v_ref_embedding vector(512);
    v_ref_category VARCHAR(255);
BEGIN
    SELECT oe.visual_embedding, dobj.general_category
    INTO v_ref_embedding, v_ref_category
    FROM monitoring.object_embedding oe
    JOIN monitoring.detected_object dobj ON oe.object_id = dobj.object_id
    WHERE oe.object_id = p_ref_id;

    --- Si no existe el objeto o no tiene embedding, salir sin resultados
    IF NOT FOUND THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT 
        oe.object_id AS objeto_encontrado_id,
        dobj.general_category AS tipo,
        (oe.visual_embedding <=> v_ref_embedding)::FLOAT AS distancia_coseno,
        c.camera_name AS camara_origen,
        de.timestamp_triggered AS fecha_evento
    FROM 
        monitoring.object_embedding oe
    JOIN 
        monitoring.detected_object dobj ON oe.object_id = dobj.object_id
    JOIN 
        monitoring.detection_event de ON dobj.event_id = de.event_id
    JOIN
        monitoring.camera c ON de.operational_id = c.operational_id
    WHERE 
        oe.object_id != p_ref_id --- Excluir el propio objeto
        AND dobj.general_category = v_ref_category
        AND (oe.visual_embedding <=> v_ref_embedding) <= p_threshold
    ORDER BY 
        distancia_coseno ASC
    LIMIT 
        p_max_results;
END;
$$;