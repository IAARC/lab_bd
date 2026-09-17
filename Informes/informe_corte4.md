# Universidad Simón Bolívar
### Departamento de Computación y Tecnología de la Información
### CI-3391: Taller de Bases de Datos I — Corte 4
**Informe Técnico: API RESTful para Gestión y Analítica de Videovigilancia Inteligente**

---

### 1. Introducción

Este proyecto aborda la construcción de una API RESTful para un sistema de videovigilancia inteligente. Actúa como interfaz entre clientes (cámaras, sensores) y una base de datos PostgreSQL (`pgvector` + rutinas PL/pgSQL). El objetivo es proveer una arquitectura eficiente que garantice consistencia de datos, control transaccional y búsquedas por similitud semántica mediante embeddings de 512 dimensiones.

---

### 2. Explicación de Endpoints

#### 2.1. Operaciones CRUD (Entregable 4A)
* **Ubicaciones (`/ubicaciones`):** `GET`, `POST`, `PUT` y `DELETE` para gestionar zonas físicas. El `PUT` usa `COALESCE` para actualizaciones parciales.
* **Cámaras (`/camaras`):** `GET`, `POST` y `PUT` para auditar el inventario, vincular cámaras a ubicaciones y modificar su estado.
* **Eventos (`/eventos`):** `GET` (últimos 100) y `POST` para registrar detecciones, soportando de manera opcional vectores de 512 dimensiones.

#### 2.2. Endpoints Analíticos (Entregable 4B)
Integran la lógica PL/pgSQL previamente desarrollada en la BD.
* **`GET /analytics/cameras/{id}/traffic`**: Invoca `get_camera_traffic` para medir el flujo de detecciones por hora.
* **`GET /analytics/zones/{tipo}`**: Invoca `get_zone_summary` devolviendo métricas de seguridad por zona.
* **`GET /analytics/alerts/summary`**: Ejecuta una agregación (`GROUP BY`) para contar las alertas de los últimos $N$ días por cámara y severidad.

#### 2.3. Endpoints Vectoriales (Entregable 4C)
* **`GET /objects/{id}/similar`**: Ejecuta `find_similar_objects` buscando detecciones históricas visualmente parecidas a un objeto de referencia.
* **`POST /search/similar`**: Recibe un `embedding` (512 floats) y busca objetos calculando la distancia coseno `(<=>)` al vuelo, soportando filtros por categoría.

#### 2.4. Carga Masiva CSV (Entregable 4F)
* **`POST /csv`**: Procesa un CSV ejecutando un *upsert* (`INSERT ... ON CONFLICT DO UPDATE`). Evalúa `xmax = 0` para discernir de forma atómica si cada fila fue una inserción o actualización nueva, todo protegido por *savepoints*.

---

### 3. Códigos de Estado HTTP

* **`200 OK`**: Petición procesada exitosamente.
* **`201 Created`**: Entidad creada con éxito.
* **`204 No Content`**: Recurso eliminado correctamente.
* **`400 Bad Request`**: Formato de entrada (ej. CSV) inválido.
* **`404 Not Found`**: El identificador de la entidad no existe.
* **`422 Unprocessable Entity`**: Error de validación en datos Pydantic (ej. el vector enviado no tiene 512 dimensiones).

---

### 4. Conclusiones

La arquitectura cumple de manera robusta con los requerimientos estipulados:
1. **Separación de responsabilidades:** Clara división entre validación (Pydantic), rutas web (FastAPI) y datos (psycopg3).
2. **Rendimiento optimizado:** Descartar un ORM habilitó el aprovechamiento directo del potencial analítico y vectorial de PostgreSQL.
3. **Estabilidad:** El manejo inteligente de concurrencia y la estrategia de control transaccional por savepoints proveen estabilidad garantizada ante cargas pesadas.
