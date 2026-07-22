from config.db import get_db

def get_db_session():
    """
    Dependency para inyectar la sesión de base de datos en los endpoints de FastAPI (Depends(get_db_session)).
    Delega en el context manager canónico get_db() de config/db.py.
    """
    with get_db() as db:
        yield db

__all__ = ["get_db_session", "get_db"]

