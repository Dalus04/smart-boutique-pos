import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
import models  # Asegura que todos los modelos se importen y se registren en SQLAlchemy

from config.settings import DATABASE_URL, DB_ECHO

# Crear el motor de la base de datos
engine = create_engine(
    DATABASE_URL,
    echo=DB_ECHO,  # Configurable mediante entorno (DB_ECHO/ENVIRONMENT)
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
