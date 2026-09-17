## 1. Descripción General del Proyecto

Este repositorio contiene la solución integral para el diseño, implementación, optimización analítica y exposición mediante API RESTful de una base de datos relacional para un **sistema de seguridad física basado en visión artificial**.

El sistema procesa y almacena información proveniente de cámaras de videovigilancia distribuidas en zonas físicas, captura detecciones de objetos (personas y vehículos), genera alertas automáticas ante intrusiones en zonas restringidas, y soporta **búsqueda y re-identificación semántica** mediante vectores de características densas de 512 dimensiones generados por modelos de visión computacional, utilizando la extensión **`pgvector`** de PostgreSQL.

---

## 2. Estructura del Repositorio

A continuación se detalla la organización de carpetas y componentes del proyecto:

```text
lab_bd/
├── Corte3/                       # Modelado de BD, funciones PL/pgSQL, triggers y seed
│   ├── schema.sql                
│   ├── functions.sql             
│   ├── triggers.sql              
│   ├── generate_seed.py          
│   └── seed_100.csv              # Dataset de prueba desnormalizado
│
├── Corte4/                       # Backend API
│   ├── app/
│   │   ├── routers/              # Controladores y definición de endpoints
│   │   │   ├── ubicaciones.py    
│   │   │   ├── camaras.py        
│   │   │   ├── eventos.py        
│   │   │   ├── analytics.py      
│   │   │   ├── vector.py         
│   │   │   └── extra_csv.py      
│   │   ├── schemas/              # Modelos de validación Pydantic v2
│   │   │   ├── ubicacion.py      
│   │   │   ├── camara.py         
│   │   │   ├── evento.py         
│   │   │   ├── analytics.py      
│   │   │   └── vector.py         
│   │   ├── config.py             
│   │   └── database.py           
│   ├── main.py                   
│   ├── requirements.txt          
│   ├── .env                      
│
├── Informes/                     # Documentación técnica y memorias de diseño
│   ├── informe_corte2.md         
│   ├── informe_corte3.md         
│   └── informe_corte4.md         
│
├── .gitignore                   
└── README.md                     
```

---

## 3. Resumen

### Corte 3: Base de Datos, PL/pgSQL y Triggers
* **Esquema Relacional + `pgvector`:** Modelado normalizado en PostgreSQL con soporte para vectores de 512 dimensiones (`vector(512)`).
* **Funciones PL/pgSQL:**
  * `get_camera_traffic(id, from, to)`: Agrupa detecciones por hora del día (0-23).
  * `get_zone_summary(tipo)`: Resumen de cámaras activas, detecciones y alertas por zona.
  * `find_similar_objects(id, threshold, limit)`: Búsqueda de objetos por similitud coseno (`<=>`).
* **Triggers:**
  * `trg_alerta_zona_peatonal`: Genera alerta automática (`high`) si entra un `VEHICLE` a zona `peatonal_restringida`.
  * `trg_audit_camara`: Registra en `camera_audit` cuando una cámara pasa a estado `inactive`.
* **Poblado (`generate_seed.py`):** Script en Python/Pandas que limpia, normaliza y carga `seed_100.csv` asegurando llaves foráneas y secuencias consistentes.

### Corte 4: Backend API (FastAPI)
* **Stack:** FastAPI + `psycopg3` (SQL directo con pool de conexiones, sin ORM) + Pydantic v2.
* **Manejo Transaccional:** Uso de *savepoints* (`db.transaction()`) en ingesta CSV para procesar fila por fila sin cancelar la carga ante fallos aislados.
* **Integración Vectorial:** Búsqueda semántica directa en PostgreSQL usando el operador de distancia coseno `<=>`.

---

## 4. Endpoints de la API

### Ubicaciones (`/ubicaciones`)
* `GET /ubicaciones`: Lista todas las ubicaciones.
* `POST /ubicaciones`: Registra una ubicación (`nombre`, `tipo_zona`, `descripcion`).
* `PUT /ubicaciones/{id}`: Actualiza parcialmente una ubicación.
* `DELETE /ubicaciones/{id}`: Elimina una ubicación.

### Cámaras (`/camaras`)
* `GET /camaras`: Lista todas las cámaras registradas.
* `GET /camaras/{id}`: Obtiene el detalle de una cámara.
* `POST /camaras`: Registra una cámara (`codigo`, `modelo`, `estado`, `id_ubicacion`).
* `PUT /camaras/{id}`: Modifica estado o parámetros de una cámara.

### Eventos (`/eventos`)
* `GET /eventos`: Retorna los últimos 100 eventos de detección.
* `GET /eventos/{id}`: Retorna un evento por su ID.
* `POST /eventos`: Inserta un evento (admite `embedding` vectorial opcional).

### Analítica (`/analytics`)
* `GET /analytics/cameras/{id}/traffic?from=YYYY-MM-DD&to=YYYY-MM-DD`: Tráfico horario invocando `get_camera_traffic`.
* `GET /analytics/zones/{tipo}`: Resumen de zona invocando `get_zone_summary`.
* `GET /analytics/alerts/summary?days=30`: Total de alertas agrupadas por cámara y severidad.

### Búsqueda Vectorial
* `GET /objects/{id}/similar?threshold=0.20&limit=5`: Objetos similares a uno existente vía `find_similar_objects`.
* `POST /search/similar?tipo=persona&limit=5`: Búsqueda directa por vector. Body: `{"embedding": [512 floats]}`.

### Ingesta Masiva
* `POST /csv`: Carga archivo CSV de eventos (`multipart/form-data`). Retorna balance de filas agregadas, actualizadas y fallidas.

---

## 5. Cómo Ejecutar el Proyecto

### Prerrequisitos
* **Python 3.10+** instalado.
* **PostgreSQL 15+** con la extensión `pgvector` habilitada.
* Las tablas y funciones del Corte 3 (`schema.sql`, `functions.sql`, `triggers.sql`) deben estar cargadas en la base de datos.

### Pasos para Levantar la API (Corte 4)

1. **Ubicarse en el directorio del backend:**
   ```bash
   cd Corte4
   ```

2. **Crear y activar un entorno virtual:**
   * **Windows (PowerShell):**
     ```powershell
     python -m venv env
     .\env\Scripts\Activate.ps1
     ```
   * **Linux/macOS:**
     ```bash
     python3 -m venv env
     source env/bin/activate
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar la Base de Datos:**
   Crea un archivo `.env` en la raíz de la carpeta `Corte4/` con tus credenciales de PostgreSQL:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=videovigilancia_db
   DB_USER=postgres
   DB_PASSWORD=tu_contraseña
   ```

5. **Iniciar el Servidor:**
   ```bash
   uvicorn main.py --reload --port 8000
   ```

6. **Explorar y Probar los Endpoints:**
   Ve a tu navegador y abre la interfaz interactiva de Swagger UI:
   * [http://localhost:8000/docs](http://localhost:8000/docs)
