import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base

# Cargar variables de entorno desde el archivo .env
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "para_ti_boutique")

# Construir la URL de conexión para MySQL usando PyMySQL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Crear el motor de la base de datos
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Imprime las consultas SQL generadas en la consola (útil para desarrollo)
    pool_pre_ping=True  # Verifica la validez de las conexiones antes de usarlas
)

# Fábrica de sesiones configurada estrictamente como transaccional (autocommit=False, autoflush=False)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

@contextmanager
def get_db():
    """
    Generador de contexto para obtener una sesión de base de datos.
    Garantiza que la sesión se cierre correctamente tras su uso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
