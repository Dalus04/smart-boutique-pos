import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime, timedelta

from api.dependencies import get_db_session
from models.actores import Cliente, Proveedor
from models.pos import Venta, DetalleVenta
from models.suministro import Compra, DetalleCompra
from models.catalogo import Producto, Categoria

router = APIRouter(
    prefix="/api/v1/actores",
    tags=["Actores Comerciales"]
)

# Schemas Cliente
class ClienteBase(BaseModel):
    tipoDocumento: str = Field(..., description="DNI o RUC")
    numeroDocumento: str = Field(..., description="Exactamente 8 u 11 dígitos")
    nombres: str
    apellidos: str
    telefono: Optional[str] = None
    correoElectronico: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(ClienteBase):
    pass

# Schemas Proveedor
class ProveedorBase(BaseModel):
    tipoDocumento: str = Field(default="RUC")
    numeroDocumento: str = Field(..., description="Exactamente 11 dígitos")
    nombreRazonSocial: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    correoElectronico: Optional[str] = None

class ProveedorCreate(ProveedorBase):
    pass

class ProveedorUpdate(ProveedorBase):
    pass

# --- ENDPOINTS CLIENTES ---

@router.get("/clientes")
def get_clientes(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(20, ge=1, le=100, description="Registros por página"),
    q: Optional[str] = Query(None, description="Búsqueda por documento, nombres o apellidos"),
    db: Session = Depends(get_db_session)
):
    subq_cat = (
        db.query(Categoria.nombreCategoria)
        .join(Producto, Categoria.idCategoria == Producto.idCategoria)
        .join(DetalleVenta, Producto.idProducto == DetalleVenta.idProducto)
        .join(Venta, DetalleVenta.idVenta == Venta.idVenta)
        .filter(Venta.idCliente == Cliente.idCliente)
        .group_by(Categoria.nombreCategoria)
        .order_by(func.sum(DetalleVenta.cantidad).desc())
        .limit(1)
        .scalar_subquery()
    )

    base_query = db.query(
        Cliente, 
        func.count(Venta.idVenta).label("frecuencia"),
        func.max(Venta.fechaVenta).label("ultima_transaccion"),
        func.avg(Venta.montoTotal).label("ticket_promedio"),
        subq_cat.label("especialidad")
    ).outerjoin(Venta, Cliente.idCliente == Venta.idCliente)\
     .filter(Cliente.estado == 'ACTIVO')\
     .group_by(Cliente.idCliente)

    if q:
        search_term = f"%{q}%"
        base_query = base_query.filter(or_(
            Cliente.numeroDocumento.like(search_term),
            Cliente.nombres.like(search_term),
            Cliente.apellidos.like(search_term)
        ))

    total_records = base_query.count()
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 1

    offset_val = (page - 1) * limit
    resultados = base_query.offset(offset_val).limit(limit).all()

    data = [{
        "idCliente": row.Cliente.idCliente,
        "tipoDocumento": row.Cliente.tipoDocumento,
        "numeroDocumento": row.Cliente.numeroDocumento,
        "nombres": row.Cliente.nombres,
        "apellidos": row.Cliente.apellidos,
        "telefono": row.Cliente.telefono or "-",
        "correoElectronico": row.Cliente.correoElectronico or "-",
        "frecuencia": row.frecuencia or 0,
        "ultima_transaccion": row.ultima_transaccion.isoformat() if row.ultima_transaccion else None,
        "ticket_promedio": float(row.ticket_promedio or 0),
        "especialidad": row.especialidad or "Sin preferencia"
    } for row in resultados]

    return {
        "data": data,
        "total_pages": total_pages,
        "current_page": page,
        "total_records": total_records
    }

@router.post("/clientes")
def create_cliente(payload: ClienteCreate, db: Session = Depends(get_db_session)):
    existente = db.query(Cliente).filter(Cliente.numeroDocumento == payload.numeroDocumento).first()
    if existente:
        raise HTTPException(status_code=400, detail="El número de documento ya está registrado.")
    
    nuevo_cliente = Cliente(**payload.model_dump())
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return {"status": "success", "idCliente": nuevo_cliente.idCliente}

@router.put("/clientes/{id}")
def update_cliente(id: int, payload: ClienteUpdate, db: Session = Depends(get_db_session)):
    cliente = db.query(Cliente).filter(Cliente.idCliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    existente = db.query(Cliente).filter(
        Cliente.numeroDocumento == payload.numeroDocumento, 
        Cliente.idCliente != id
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="El número de documento ya pertenece a otro cliente.")
        
    for var, value in payload.model_dump().items():
        setattr(cliente, var, value)
        
    db.commit()
    return {"status": "success"}

@router.patch("/clientes/{id}/inactivar")
def inactivar_cliente(id: int, db: Session = Depends(get_db_session)):
    cliente = db.query(Cliente).filter(Cliente.idCliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    cliente.estado = 'INACTIVO'
    db.commit()
    return {"status": "success", "message": "Cliente inactivado exitosamente", "idCliente": id}

# --- ENDPOINTS PROVEEDORES ---

@router.get("/proveedores")
def get_proveedores(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(20, ge=1, le=100, description="Registros por página"),
    q: Optional[str] = Query(None, description="Búsqueda por RUC o Razón Social"),
    db: Session = Depends(get_db_session)
):
    subq_cat = (
        db.query(Categoria.nombreCategoria)
        .join(Producto, Categoria.idCategoria == Producto.idCategoria)
        .join(DetalleCompra, Producto.idProducto == DetalleCompra.idProducto)
        .join(Compra, DetalleCompra.idCompra == Compra.idCompra)
        .filter(Compra.idProveedor == Proveedor.idProveedor)
        .group_by(Categoria.nombreCategoria)
        .order_by(func.sum(DetalleCompra.cantidad).desc())
        .limit(1)
        .scalar_subquery()
    )

    base_query = db.query(
        Proveedor,
        func.count(Compra.idCompra).label("frecuencia"),
        func.max(Compra.fechaCompra).label("ultima_transaccion"),
        func.avg(Compra.montoTotal).label("ticket_promedio"),
        subq_cat.label("especialidad")
    ).outerjoin(Compra, Proveedor.idProveedor == Compra.idProveedor)\
     .filter(Proveedor.estado == 'ACTIVO')\
     .group_by(Proveedor.idProveedor)

    if q:
        search_term = f"%{q}%"
        base_query = base_query.filter(or_(
            Proveedor.numeroDocumento.like(search_term),
            Proveedor.nombreRazonSocial.like(search_term)
        ))

    total_records = base_query.count()
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 1

    offset_val = (page - 1) * limit
    resultados = base_query.offset(offset_val).limit(limit).all()

    data = [{
        "idProveedor": row.Proveedor.idProveedor,
        "tipoDocumento": row.Proveedor.tipoDocumento,
        "numeroDocumento": row.Proveedor.numeroDocumento,
        "nombreRazonSocial": row.Proveedor.nombreRazonSocial,
        "telefono": row.Proveedor.telefono or "-",
        "direccion": row.Proveedor.direccion or "-",
        "correoElectronico": row.Proveedor.correoElectronico or "-",
        "frecuencia": row.frecuencia or 0,
        "ultima_transaccion": row.ultima_transaccion.isoformat() if row.ultima_transaccion else None,
        "ticket_promedio": float(row.ticket_promedio or 0),
        "especialidad": row.especialidad or "Sin suministros"
    } for row in resultados]

    return {
        "data": data,
        "total_pages": total_pages,
        "current_page": page,
        "total_records": total_records
    }

@router.post("/proveedores")
def create_proveedor(payload: ProveedorCreate, db: Session = Depends(get_db_session)):
    existente = db.query(Proveedor).filter(Proveedor.numeroDocumento == payload.numeroDocumento).first()
    if existente:
        raise HTTPException(status_code=400, detail="El RUC ya está registrado.")
    
    nuevo_proveedor = Proveedor(**payload.model_dump())
    db.add(nuevo_proveedor)
    db.commit()
    db.refresh(nuevo_proveedor)
    return {"status": "success", "idProveedor": nuevo_proveedor.idProveedor}

@router.put("/proveedores/{id}")
def update_proveedor(id: int, payload: ProveedorUpdate, db: Session = Depends(get_db_session)):
    proveedor = db.query(Proveedor).filter(Proveedor.idProveedor == id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    existente = db.query(Proveedor).filter(
        Proveedor.numeroDocumento == payload.numeroDocumento, 
        Proveedor.idProveedor != id
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="El RUC ya pertenece a otro proveedor.")
        
    for var, value in payload.model_dump().items():
        setattr(proveedor, var, value)
        
    db.commit()
    return {"status": "success"}

@router.patch("/proveedores/{id}/inactivar")
def inactivar_proveedor(id: int, db: Session = Depends(get_db_session)):
    proveedor = db.query(Proveedor).filter(Proveedor.idProveedor == id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    proveedor.estado = 'INACTIVO'
    db.commit()
    return {"status": "success", "message": "Proveedor inactivado exitosamente", "idProveedor": id}
