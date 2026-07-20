from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

from api.dependencies import get_db_session
from models.suministro import Compra, DetalleCompra, Inventario
from models.catalogo import Producto
from models.actores import Proveedor
from services.prediccion import PrediccionService

router = APIRouter(
    prefix="/api/v1/compras",
    tags=["Suministro (Compras)"]
)

@router.get("/sugerencias")
def obtener_sugerencias_compra(db: Session = Depends(get_db_session)):
    """
    Retorna el top 5 de productos sugeridos para compra basados en su velocidad de venta y stock actual.
    Además incluye el proveedor sugerido (el último o más frecuente).
    """
    productos_activos = db.query(Producto).filter(Producto.estado == 'ACTIVO').all()
    
    sugerencias = []
    for prod in productos_activos:
        # Usamos el servicio de predicción
        reporte = PrediccionService.evaluar_producto(db, prod.idProducto, dias_entrega=7)
        
        velocidad = reporte["velocidad_venta_diaria"]
        stock_actual = reporte["stock_actual"]
        riesgo = reporte["riesgo"]
        
        # Queremos cubrir 30 días de ventas
        sugerencia_compra = max(0, int((velocidad * 30) - stock_actual))
        
        if sugerencia_compra > 0 and riesgo in ["Riesgo Alto", "Riesgo Medio", "Crítico"]:
            # Pequeña frase de impacto
            if velocidad > 1:
                contexto = "Alta rotación. Riesgo de quiebre inminente."
            else:
                contexto = "Stock bajo. Reposición preventiva."
                
            sugerencias.append({
                "idProducto": prod.idProducto,
                "codigoBarras": prod.codigoBarras,
                "nombre": prod.nombre,
                "stockActual": stock_actual,
                "costo": float(prod.costoProducto or 0.0),
                "precioLista": float(prod.precioLista or 0.0),
                "velocidadDiaria": round(velocidad, 2),
                "sugerencia": sugerencia_compra,
                "contexto": contexto,
                "prioridad": sugerencia_compra * velocidad # heuristic
            })
            
    # Ordenar por prioridad descendente y tomar Top 5
    sugerencias.sort(key=lambda x: x["prioridad"], reverse=True)
    sugerencias = sugerencias[:5]
    
    # Proveedor sugerido (el último registrado o el primero activo)
    proveedor_sugerido = db.query(Proveedor).filter(Proveedor.estado == 'ACTIVO').first()
    
    return {
        "proveedorSugerido": proveedor_sugerido.idProveedor if proveedor_sugerido else None,
        "sugerencias": sugerencias
    }


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
