from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from api.dependencies import get_db_session
from api.schemas.actores import (
    ClienteCreate,
    ClienteUpdate,
    ProveedorCreate,
    ProveedorUpdate,
)
from services.actores import ActoresService

router = APIRouter(
    prefix="/api/v1/actores",
    tags=["Actores Comerciales"]
)

# --- ENDPOINTS CLIENTES ---

@router.get("/clientes")
def get_clientes(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: Optional[str] = Query(None, description="Búsqueda por documento, nombres o apellidos"),
    db: Session = Depends(get_db_session)
):
    return ActoresService.get_clientes_paginados(db=db, page=page, limit=limit, q=q)

@router.post("/clientes")
def create_cliente(payload: ClienteCreate, db: Session = Depends(get_db_session)):
    return ActoresService.create_cliente(db=db, payload=payload)

@router.put("/clientes/{id}")
def update_cliente(id: int, payload: ClienteUpdate, db: Session = Depends(get_db_session)):
    return ActoresService.update_cliente(db=db, cliente_id=id, payload=payload)

@router.patch("/clientes/{id}/inactivar")
def inactivar_cliente(id: int, db: Session = Depends(get_db_session)):
    return ActoresService.inactivar_cliente(db=db, cliente_id=id)

# --- ENDPOINTS PROVEEDORES ---

@router.get("/proveedores")
def get_proveedores(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: Optional[str] = Query(None, description="Búsqueda por RUC o Razón Social"),
    db: Session = Depends(get_db_session)
):
    return ActoresService.get_proveedores_paginados(db=db, page=page, limit=limit, q=q)

@router.post("/proveedores")
def create_proveedor(payload: ProveedorCreate, db: Session = Depends(get_db_session)):
    return ActoresService.create_proveedor(db=db, payload=payload)

@router.put("/proveedores/{id}")
def update_proveedor(id: int, payload: ProveedorUpdate, db: Session = Depends(get_db_session)):
    return ActoresService.update_proveedor(db=db, proveedor_id=id, payload=payload)

@router.patch("/proveedores/{id}/inactivar")
def inactivar_proveedor(id: int, db: Session = Depends(get_db_session)):
    return ActoresService.inactivar_proveedor(db=db, proveedor_id=id)
