"""
Configuración centralizada del sistema basada en variables de entorno.

Permite alternar de forma segura entre entornos (development, production, testing)
sin hardcodear opciones sensibles ni exponer registros en producción.
"""
import os
from dotenv import load_dotenv

# Cargar variables del archivo .env si existe
load_dotenv()

# Entorno de ejecución: 'development', 'production', 'testing'
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# ── Configuración de Base de Datos ───────────────────────────────────────────
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "para_ti_boutique")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Control de logs SQL (echo).
# Por defecto False en producción para evitar filtración de datos sensibles.
_db_echo_env = os.getenv("DB_ECHO")
if _db_echo_env is not None:
    DB_ECHO = _db_echo_env.lower() in ("true", "1", "yes")
else:
    DB_ECHO = ENVIRONMENT == "development"

# ── Configuración de CORS ─────────────────────────────────────────────────────
# Por defecto '*' en desarrollo; restringido en producción según CORS_ORIGINS.
_cors_origins_env = os.getenv("CORS_ORIGINS")
if _cors_origins_env is not None:
    CORS_ORIGINS = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
elif ENVIRONMENT == "development":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
