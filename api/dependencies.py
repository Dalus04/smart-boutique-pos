from config.db import get_db
from sqlalchemy.orm import Session
from models.usuarios import Usuario

def get_db_session():
    """
    Dependency para inyectar la sesión de base de datos en los endpoints de FastAPI (Depends(get_db_session)).
    Delega en el context manager canónico get_db() de config/db.py.
    """
    with get_db() as db:
        yield db

def obtener_id_usuario_defecto(db: Session) -> int:
    """
    Obtiene el ID de un usuario existente o crea un usuario por defecto si la tabla está vacía.
    Evita fallos de Foreign Key constraint (1452) en operaciones de POS y Compras.
    """
    usuario = db.query(Usuario).filter(Usuario.estado == "ACTIVO").first()
    if not usuario:
        usuario = db.query(Usuario).first()
    if not usuario:
        usuario = Usuario(
            nombres="Admin",
            apellidos="Sistema",
            nombreUsuario="admin",
            contrasena="123456",
            rol="ADMINISTRADOR",
            estado="ACTIVO"
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    return usuario.idUsuario

__all__ = ["get_db_session", "get_db", "obtener_id_usuario_defecto"]


