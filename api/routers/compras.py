from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from decimal import Decimal

from api.dependencies import get_db_session
from models.suministro import Compra, DetalleCompra, Inventario
from models.catalogo import Producto

router = APIRouter(
    prefix="/api/v1/compras",
    tags=["Suministro (Compras)"]
)

class CompraItem(BaseModel):
    idProducto: int
    cantidad: int
    costoUnitario: float

class RegistrarCompraPayload(BaseModel):
    idProveedor: int
    items: List[CompraItem]
    montoTotal: float

@router.post("/registrar")
def registrar_compra(payload: RegistrarCompraPayload, db: Session = Depends(get_db_session)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="La orden de compra no puede estar vacía")
        
    id_usuario = 1 # Hardcodeado temporalmente
    
    try:
        # 1. Crear Cabecera de Compra
        compra = Compra(
            idProveedor=payload.idProveedor,
            idUsuario=id_usuario,
            montoTotal=Decimal(str(payload.montoTotal))
        )
        db.add(compra)
        db.flush() # Para obtener idCompra
        
        # 2. Procesar Detalles y Actualizar Inventario Atómicamente
        for item in payload.items:
            # Insertar el detalle
            detalle = DetalleCompra(
                idCompra=compra.idCompra,
                idProducto=item.idProducto,
                cantidad=item.cantidad,
                costoUnitario=Decimal(str(item.costoUnitario)),
                subtotal=Decimal(str(item.cantidad * item.costoUnitario))
            )
            db.add(detalle)
            
            # Bloquear registro de inventario e incrementarlo
            inventario = db.query(Inventario).filter(Inventario.idProducto == item.idProducto).with_for_update().first()
            if inventario:
                inventario.cantidadDisponible += item.cantidad
            else:
                # Si por alguna razón el producto no tenía registro de inventario, crearlo
                nuevo_inv = Inventario(
                    idProducto=item.idProducto,
                    cantidadDisponible=item.cantidad
                )
                db.add(nuevo_inv)
                
            # Opcional (Buena Práctica): Actualizar el costo del producto en el catálogo al último costo de compra
            producto = db.query(Producto).filter(Producto.idProducto == item.idProducto).first()
            if producto:
                producto.costoProducto = Decimal(str(item.costoUnitario))
                
        # 3. Consolidar Transacción
        db.commit()
        return {"status": "success", "idCompra": compra.idCompra, "mensaje": "Compra registrada e inventario actualizado"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error registrando compra: {str(e)}")
