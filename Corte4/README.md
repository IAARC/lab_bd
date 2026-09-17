# CI-3391 Taller de Bases de Datos I — Corte 4
## API RESTful de Videovigilancia Inteligente

Backend desarrollado con FastAPI y PostgreSQL (con soporte para `pgvector`) para la gestión de cámaras, ubicaciones, eventos y analíticas de videovigilancia.

---

### Requisitos previos

* Python 3.10 o superior
* PostgreSQL con la extensión `pgvector` habilitada y las funciones PL/pgSQL de la Fase 3 instaladas (`get_camera_traffic`, `get_zone_summary`, `find_similar_objects`).

---

### Instalación y configuración

1. **Clonar el repositorio o ubicarse en la carpeta del proyecto:**
   ```bash
   cd videovigilancia-api
   ```

2. **Crear y activar un entorno virtual:**
   * En Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * En Linux/macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   Crear un archivo `.env` en la raíz del proyecto (o editar el existente) con las credenciales de la base de datos:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=videovigilancia_db
   DB_USER=postgres
   DB_PASSWORD=tu_contraseña
   ```

---

### Ejecución del servidor

Para iniciar la API en modo de desarrollo con recarga automática:

```bash
uvicorn main.py --reload --port 8000
```

Una vez levantado, la documentación interactiva Swagger UI estará disponible directamente en:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Estructura del proyecto

```text
videovigilancia-api/
├── app/
│   ├── routers/
│   │   ├── ubicaciones.py    # CRUD de ubicaciones
│   │   ├── camaras.py        # CRUD de cámaras
│   │   ├── eventos.py        # Registro y consulta de eventos
│   │   ├── analytics.py      # Endpoints analíticos y llamadas a PL/pgSQL
│   │   ├── vector.py         # Búsqueda semántica con pgvector
│   │   └── extra_csv.py      # Ingesta masiva CSV (opcional)
│   ├── schemas/              # Modelos Pydantic v2 para validación
│   ├── config.py             # Lectura de variables de entorno (.env)
│   └── database.py           # Pool de conexiones psycopg3 (sin ORM)
├── main.py                   # Instancia principal de FastAPI y montaje de routers
├── requirements.txt          # Dependencias del proyecto
└── README.md
```

---

### Pruebas de los endpoints

#### 1. Endpoints CRUD (Entregable 4A)

* **Listar ubicaciones:**
  ```bash
  curl -X GET "http://localhost:8000/ubicaciones"
  ```
* **Crear una ubicación:**
  ```bash
  curl -X POST "http://localhost:8000/ubicaciones" \
       -H "Content-Type: application/json" \
       -d '{"nombre": "Entrada Principal", "tipo_zona": "exterior", "descripcion": "Acceso vehicular"}'
  ```
* **Crear una cámara:**
  ```bash
  curl -X POST "http://localhost:8000/camaras" \
       -H "Content-Type: application/json" \
       -d '{"codigo": "CAM-001", "modelo": "Hikvision 4K", "estado": "activa", "id_ubicacion": 1}'
  ```
* **Registrar un evento:**
  ```bash
  curl -X POST "http://localhost:8000/eventos" \
       -H "Content-Type: application/json" \
       -d '{"id_camara": 1, "tipo_objeto": "persona", "confianza": 0.94}'
  ```

#### 2. Endpoints Analíticos (Entregable 4B)

* **Tráfico de una cámara por rango de fechas (llama a `get_camera_traffic`):**
  ```bash
  curl -X GET "http://localhost:8000/analytics/cameras/1/traffic?from=2026-01-01&to=2026-06-30"
  ```
* **Resumen por tipo de zona (llama a `get_zone_summary`):**
  ```bash
  curl -X GET "http://localhost:8000/analytics/zones/exterior"
  ```
* **Resumen de alertas por cámara y severidad:**
  ```bash
  curl -X GET "http://localhost:8000/analytics/alerts/summary?days=30"
  ```

#### 3. Endpoints Vectoriales (Entregable 4C)

* **Objetos visualmente similares a un evento (llama a `find_similar_objects`):**
  ```bash
  curl -X GET "http://localhost:8000/objects/1/similar?threshold=0.20&limit=5"
  ```
* **Búsqueda vectorial con embedding de 512 dimensiones:**
  ```bash
  curl -X POST "http://localhost:8000/search/similar?tipo=persona&limit=5" \
       -H "Content-Type: application/json" \
       -d '{"embedding": [0.012, -0.045, ...]}' # Vector de 512 números float
  ```

#### 4. Carga Masiva CSV (Entregable 4F)

* **Subida de archivo CSV:**
  ```bash
  curl -X POST "http://localhost:8000/csv" \
       -F "file=@datos_eventos.csv"
  ```
  Retorna un JSON con el balance de filas procesadas:
  ```json
  {
    "filas_agregadas": 120,
    "filas_actualizadas": 15,
    "filas_no_subidas": 2
  }
  ```
