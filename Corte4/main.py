from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from app.database import pool
from app.routers import ubicaciones, camaras, eventos, analytics, vector, extra_csv

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    pool.close()

# 1. Primero instanciamos la aplicación
app = FastAPI(
    title="API de Videovigilancia Inteligente",
    description="Backend analítico y vectorial - CI-3391",
    version="1.0.0",
    lifespan=lifespan
)

# 2. Redirección al Swagger en la raíz
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

# 3. Incluimos los módulos de endpoints
app.include_router(ubicaciones.router)
app.include_router(camaras.router)
app.include_router(eventos.router)
app.include_router(analytics.router)
app.include_router(vector.router)
app.include_router(extra_csv.router)