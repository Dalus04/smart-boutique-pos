from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db_session, obtener_id_usuario_defecto
from api.schemas.compras import (
    SolicitudReposicionCreate,
    RegistrarCompraPayload,
    EstadoCompraPayload,
    SyncBorradorPayload,
)
from services.compras import ComprasService

router = APIRouter(
    prefix="/api/v1/compras",
    tags=["Suministro (Compras)"]
)

@router.get("/sugerencias")
def obtener_sugerencias_compra(db: Session = Depends(get_db_session)):
    return ComprasService.obtener_sugerencias_compra(db=db)

@router.post("/solicitud")
def crear_solicitud(payload: SolicitudReposicionCreate, db: Session = Depends(get_db_session)):
    return ComprasService.crear_solicitud(db=db, payload=payload)

@router.get("/solicitudes/pendientes")
def obtener_solicitudes_pendientes(db: Session = Depends(get_db_session)):
    return ComprasService.obtener_solicitudes_pendientes(db=db)

@router.post("/registrar")
def registrar_compra(payload: RegistrarCompraPayload, db: Session = Depends(get_db_session)):
    id_usuario = obtener_id_usuario_defecto(db)
    return ComprasService.registrar_compra(db=db, payload=payload, id_usuario=id_usuario)

@router.put("/compra/{id_compra}/estado")
def cambiar_estado_compra(id_compra: int, payload: EstadoCompraPayload, db: Session = Depends(get_db_session)):
    return ComprasService.cambiar_estado_compra(db=db, id_compra=id_compra, payload=payload)

@router.get("/planificacion/borrador")
def obtener_borrador_activo(db: Session = Depends(get_db_session)):
    id_usuario = obtener_id_usuario_defecto(db)
    return ComprasService.obtener_borrador_activo(db=db, id_usuario=id_usuario)

@router.put("/planificacion/borrador")
def sincronizar_borrador(payload: SyncBorradorPayload, db: Session = Depends(get_db_session)):
    id_usuario = obtener_id_usuario_defecto(db)
    return ComprasService.sincronizar_borrador(db=db, payload=payload, id_usuario=id_usuario)

@router.get("/ordenes_activas")
def obtener_ordenes_activas(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Registros por página"),
    db: Session = Depends(get_db_session)
):
    return ComprasService.obtener_ordenes_activas(db=db, page=page, limit=limit)

@router.post("/planificacion/borrador/{id_compra}/consolidar")
def consolidar_orden(id_compra: int, db: Session = Depends(get_db_session)):
    return ComprasService.consolidar_orden(db=db, id_compra=id_compra)

@router.get("/historial")
def obtener_historial_global(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Registros por página"),
    db: Session = Depends(get_db_session)
):
    return ComprasService.obtener_historial_global(db=db, page=page, limit=limit)

@router.get("/historial/{id_compra}/detalles")
def obtener_detalles_compra(id_compra: int, db: Session = Depends(get_db_session)):
    return ComprasService.obtener_detalles_compra(db=db, id_compra=id_compra)

@router.get("/historial_producto/{id_producto}")
def obtener_historial_producto(id_producto: int, db: Session = Depends(get_db_session)):
    return ComprasService.obtener_historial_producto(db=db, id_producto=id_producto)
