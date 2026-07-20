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

# Helper para calcular la Acción Recomendada
def calcular_accion(frecuencia: int, ultima_transaccion, es_cliente: bool) -> dict:
    if not ultima_transaccion:
        if es_cliente:
            return {
                "texto": "Enviar Catálogo de Bienvenida", 
                "explicacion": "Cliente registrado sin compras anteriores. Presentar la colección actual facilitará su primera transacción.",
                "badge_class": "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
            }
        else:
            return {
                "texto": "Solicitar Lista de Precios", 
                "explicacion": "Proveedor registrado sin pedidos previos. Solicitar catálogo para evaluar su oferta y condiciones comerciales.",
                "badge_class": "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
            }

    # Determinar fecha
    if isinstance(ultima_transaccion, datetime):
        ultima_date = ultima_transaccion.date()
    elif isinstance(ultima_transaccion, str):
        ultima_date = datetime.strptime(ultima_transaccion, "%Y-%m-%d").date()
    else:
        ultima_date = ultima_transaccion

    dias = (date.today() - ultima_date).days
    is_activo = dias <= 30
    is_frecuente = frecuencia >= 3

    if es_cliente:
        if is_frecuente and is_activo:
            return {
                "texto": "Invitar al Programa VIP", 
                "explicacion": "Este cliente compra con frecuencia y mantiene un ticket superior al promedio. Ofrecer beneficios exclusivos aumenta su fidelización.",
                "badge_class": "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200 border border-emerald-700/50"
            }
        elif is_activo:
            return {
                "texto": "Sugerir Producto Complementario", 
                "explicacion": "Cliente regular con actividad reciente. Enviar sugerencias o encuesta de satisfacción para elevar el ticket.",
                "badge_class": "bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 border border-blue-700/50"
            }
        else:
            return {
                "texto": "Reactivar con Oferta Especial", 
                "explicacion": "El cliente no ha realizado compras en más de 30 días. Enviar un cupón de descuento puede incentivar su retorno.",
                "badge_class": "bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200 border border-amber-700/50"
            }
    else:
        if is_frecuente and is_activo:
            return {
                "texto": "Negociar Descuento por Volumen", 
                "explicacion": "Suministrador recurrente clave. Coordinar compras por volumen permite optimizar los márgenes de ganancia.",
                "badge_class": "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200 border border-emerald-700/50"
            }
        elif is_activo:
            return {
                "texto": "Programar Próximo Pedido", 
                "explicacion": "Este proveedor abastece productos importantes para la tienda. Anticipar el pedido ayuda a evitar quiebres de stock.",
                "badge_class": "bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 border border-blue-700/50"
            }
        else:
            return {
                "texto": "Solicitar Catálogo Actualizado", 
                "explicacion": "No existen pedidos recientes. Solicitar el catálogo permitirá conocer nuevos productos y precios actualizados.",
                "badge_class": "bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200 border border-amber-700/50"
            }

# --- ENDPOINTS CLIENTES ---

@router.get("/clientes")
def get_clientes(
    q: Optional[str] = Query(None, description="Búsqueda por documento, nombres o apellidos"),
    db: Session = Depends(get_db_session)
):
    # Subconsulta para obtener la categoría preferida del cliente
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

    query = db.query(
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
        query = query.filter(or_(
            Cliente.numeroDocumento.like(search_term),
            Cliente.nombres.like(search_term),
            Cliente.apellidos.like(search_term)
        ))

    resultados = query.all()

    return [{
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
        "especialidad": row.especialidad or "Sin preferencia",
        "accion_recomendada": calcular_accion(row.frecuencia or 0, row.ultima_transaccion, es_cliente=True)
    } for row in resultados]

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

# --- ENDPOINTS PROVEEDORES ---

@router.get("/proveedores")
def get_proveedores(
    q: Optional[str] = Query(None, description="Búsqueda por RUC o Razón Social"),
    db: Session = Depends(get_db_session)
):
    # Subconsulta para obtener la categoría principal suministrada por el proveedor
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

    query = db.query(
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
        query = query.filter(or_(
            Proveedor.numeroDocumento.like(search_term),
            Proveedor.nombreRazonSocial.like(search_term)
        ))

    resultados = query.all()

    return [{
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
        "especialidad": row.especialidad or "Sin suministros",
        "accion_recomendada": calcular_accion(row.frecuencia or 0, row.ultima_transaccion, es_cliente=False)
    } for row in resultados]

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
