from config.db import SessionLocal

def get_db_session():
    """
    Dependency para inyectar la sesión de base de datos en los endpoints de FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
