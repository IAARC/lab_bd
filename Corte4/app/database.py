# app/database.py
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from app.config import settings

pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=2,
    max_size=10,
    kwargs={"row_factory": dict_row}  # Retorna diccionarios en lugar de tuplas
)

def get_db():
    with pool.connection() as conn:
        yield conn