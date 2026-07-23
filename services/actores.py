import math
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi import HTTPException

from models.actores import Cliente, Proveedor
from models.pos import Venta, DetalleVenta
from models.suministro import Compra, DetalleCompra
from models.catalogo import Producto, Categoria
from api.schemas.actores import (
    ClienteCreate,
    ClienteUpdate,
    ProveedorCreate,
    ProveedorUpdate,
)

class ActoresService:
    @staticmethod
    def get_clientes_paginados(db: Session, page: int = 1, limit: int = 20, q: Optional[str] = None):
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

        if q and isinstance(q, str):
            search_term = f"%{q}%"
            base_query = base_query.filter(or_(
                Cliente.numeroDocumento.like(search_term),
                Cliente.nombres.like(search_term),
                Cliente.apellidos.like(search_term)
            ))

        page_val = page if isinstance(page, int) else 1
        limit_val = limit if isinstance(limit, int) else 20

        total_records = base_query.count()
        total_pages = math.ceil(total_records / limit_val) if total_records > 0 else 1

        offset_val = (page_val - 1) * limit_val
        resultados = base_query.offset(offset_val).limit(limit_val).all()

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

    @staticmethod
    def create_cliente(db: Session, payload: ClienteCreate):
        existente = db.query(Cliente).filter(Cliente.numeroDocumento == payload.numeroDocumento).first()
        if existente:
            raise HTTPException(status_code=400, detail="El número de documento ya está registrado.")
        
        nuevo_cliente = Cliente(**payload.model_dump())
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        return {"status": "success", "idCliente": nuevo_cliente.idCliente}

    @staticmethod
    def update_cliente(db: Session, cliente_id: int, payload: ClienteUpdate):
        cliente = db.query(Cliente).filter(Cliente.idCliente == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
            
        existente = db.query(Cliente).filter(
            Cliente.numeroDocumento == payload.numeroDocumento, 
            Cliente.idCliente != cliente_id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="El número de documento ya pertenece a otro cliente.")
            
        for var, value in payload.model_dump().items():
            setattr(cliente, var, value)
            
        db.commit()
        return {"status": "success"}

    @staticmethod
    def inactivar_cliente(db: Session, cliente_id: int):
        cliente = db.query(Cliente).filter(Cliente.idCliente == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        cliente.estado = 'INACTIVO'
        db.commit()
        return {"status": "success", "message": "Cliente inactivado exitosamente", "idCliente": cliente_id}

    @staticmethod
    def get_proveedores_paginados(db: Session, page: int = 1, limit: int = 20, q: Optional[str] = None):
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

        if q and isinstance(q, str):
            search_term = f"%{q}%"
            base_query = base_query.filter(or_(
                Proveedor.numeroDocumento.like(search_term),
                Proveedor.nombreRazonSocial.like(search_term)
            ))

        page_val = page if isinstance(page, int) else 1
        limit_val = limit if isinstance(limit, int) else 20

        total_records = base_query.count()
        total_pages = math.ceil(total_records / limit_val) if total_records > 0 else 1

        offset_val = (page_val - 1) * limit_val
        resultados = base_query.offset(offset_val).limit(limit_val).all()

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

    @staticmethod
    def create_proveedor(db: Session, payload: ProveedorCreate):
        existente = db.query(Proveedor).filter(Proveedor.numeroDocumento == payload.numeroDocumento).first()
        if existente:
            raise HTTPException(status_code=400, detail="El RUC ya está registrado.")
        
        nuevo_proveedor = Proveedor(**payload.model_dump())
        db.add(nuevo_proveedor)
        db.commit()
        db.refresh(nuevo_proveedor)
        return {"status": "success", "idProveedor": nuevo_proveedor.idProveedor}

    @staticmethod
    def update_proveedor(db: Session, proveedor_id: int, payload: ProveedorUpdate):
        proveedor = db.query(Proveedor).filter(Proveedor.idProveedor == proveedor_id).first()
        if not proveedor:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
            
        existente = db.query(Proveedor).filter(
            Proveedor.numeroDocumento == payload.numeroDocumento, 
            Proveedor.idProveedor != proveedor_id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="El RUC ya pertenece a otro proveedor.")
            
        for var, value in payload.model_dump().items():
            setattr(proveedor, var, value)
            
        db.commit()
        return {"status": "success"}

    @staticmethod
    def inactivar_proveedor(db: Session, proveedor_id: int):
        proveedor = db.query(Proveedor).filter(Proveedor.idProveedor == proveedor_id).first()
        if not proveedor:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        proveedor.estado = 'INACTIVO'
        db.commit()
        return {"status": "success", "message": "Proveedor inactivado exitosamente", "idProveedor": proveedor_id}
