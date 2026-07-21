from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

from api.dependencies import get_db_session
from models.suministro import Compra, DetalleCompra, Inventario, SolicitudReposicion
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


class SolicitudReposicionCreate(BaseModel):
    idProducto: int
    cantidad_sugerida: int
    motivo: str
    origen: Optional[str] = "Manual" # IA, Manual

@router.post("/solicitud")
def crear_solicitud(payload: SolicitudReposicionCreate, db: Session = Depends(get_db_session)):
    try:
        solicitud = SolicitudReposicion(
            idProducto=payload.idProducto,
            cantidad_sugerida=payload.cantidad_sugerida,
            motivo=payload.motivo,
            origen=payload.origen or "Manual",
            estado="Pendiente"
        )
        db.add(solicitud)
        db.commit()
        return {"status": "success", "idSolicitud": solicitud.idSolicitud, "mensaje": "Solicitud de reposición registrada"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/solicitudes/pendientes")
def obtener_solicitudes_pendientes(db: Session = Depends(get_db_session)):
    solicitudes = db.query(SolicitudReposicion).filter(SolicitudReposicion.estado == "Pendiente").all()
    resultado = []
    for sol in solicitudes:
        prod = db.query(Producto).filter(Producto.idProducto == sol.idProducto).first()
        resultado.append({
            "idSolicitud": sol.idSolicitud,
            "idProducto": sol.idProducto,
            "productoNombre": prod.nombre if prod else "Desconocido",
            "codigoBarras": prod.codigoBarras if prod else "-",
            "cantidadSugerida": sol.cantidad_sugerida,
            "motivo": sol.motivo,
            "origen": sol.origen or "IA",
            "fecha": sol.fecha_creacion.isoformat()
        })
    return {"solicitudes": resultado}

class CompraItem(BaseModel):
    idProducto: int
    cantidad: int
    costoUnitario: float

class RegistrarCompraPayload(BaseModel):
    idProveedor: int
    items: List[CompraItem]
    montoTotal: float
    estado: str = "Borrador"

@router.post("/registrar")
def registrar_compra(payload: RegistrarCompraPayload, id_usuario: int = 1, db: Session = Depends(get_db_session)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="La orden de compra no puede estar vacía")
        
    try:
        # Solo creamos la orden, NO actualizamos el stock físico aquí
        compra = Compra(
            idProveedor=payload.idProveedor,
            idUsuario=id_usuario,
            montoTotal=Decimal(str(payload.montoTotal)),
            estado=payload.estado
        )
        db.add(compra)
        db.flush()
        
        for item in payload.items:
            detalle = DetalleCompra(
                idCompra=compra.idCompra,
                idProducto=item.idProducto,
                cantidad=item.cantidad,
                costoUnitario=Decimal(str(item.costoUnitario)),
                subtotal=Decimal(str(item.cantidad * item.costoUnitario))
            )
            db.add(detalle)
            
        db.commit()
        return {"status": "success", "idCompra": compra.idCompra, "estado": compra.estado}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class EstadoCompraPayload(BaseModel):
    estado: str

@router.put("/compra/{id_compra}/estado")
def cambiar_estado_compra(id_compra: int, payload: EstadoCompraPayload, db: Session = Depends(get_db_session)):
    compra = db.query(Compra).filter(Compra.idCompra == id_compra).with_for_update().first()
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
        
    estados_validos = ["Borrador", "Emitida", "Enviada", "Confirmada", "Recepción parcial", "Completada", "Cancelada"]
    if payload.estado not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado inválido")
        
    stock_actualizado = []
    
    # Transición a Completada: mutación aditiva atómica del stock físico
    if payload.estado == "Completada" and compra.estado != "Completada":
        try:
            with db.begin_nested():
                for detalle in compra.detalles:
                    # Bloquear registro de inventario e incrementarlo
                    inventario = db.query(Inventario).filter(Inventario.idProducto == detalle.idProducto).with_for_update().first()
                    if inventario:
                        inventario.cantidadDisponible += detalle.cantidad
                    else:
                        inventario = Inventario(idProducto=detalle.idProducto, cantidadDisponible=detalle.cantidad)
                        db.add(inventario)
                    
                    # Actualizar costo del producto
                    producto = db.query(Producto).filter(Producto.idProducto == detalle.idProducto).first()
                    if producto:
                        producto.costoProducto = detalle.costoUnitario

                    # Marcar solicitudes pendientes de este producto como Agregadas
                    solicitudes = db.query(SolicitudReposicion).filter(
                        SolicitudReposicion.idProducto == detalle.idProducto,
                        SolicitudReposicion.estado == "Pendiente"
                    ).all()
                    for sol in solicitudes:
                        sol.estado = "Agregada"

                    prod_nombre = producto.nombre if producto else f"Producto #{detalle.idProducto}"
                    stock_actualizado.append({
                        "producto": prod_nombre,
                        "nuevo_stock": inventario.cantidadDisponible
                    })

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error en transacción atómica: {str(e)}")

    compra.estado = payload.estado
    db.commit()
    return {
        "status": "success", 
        "nuevo_estado": compra.estado,
        "mensaje": "Mercadería recibida y stock actualizado",
        "stock_actualizado": stock_actualizado
    }

# TODO PENDIENTE: Integrar canal de despacho automatizado (WhatsApp/Email PDF)
def despachar_orden_proveedor(id_compra: int):
    pass

class SyncBorradorItem(BaseModel):
    idProducto: int
    cantidad: int
    costoUnitario: float

class SyncBorradorPayload(BaseModel):
    idProveedor: int
    items: List[SyncBorradorItem]
    montoTotal: float

@router.get("/planificacion/borrador")
def obtener_borrador_activo(id_usuario: int = 1, db: Session = Depends(get_db_session)):
    borrador = db.query(Compra).filter(Compra.estado == "Borrador", Compra.idUsuario == id_usuario).first()
    
    if not borrador:
        return {"borrador": None}
        
    items = []
    for d in borrador.detalles:
        prod = d.producto
        items.append({
            "idProducto": d.idProducto,
            "codigoBarras": prod.codigoBarras if prod else "-",
            "nombre": prod.nombre if prod else "Desconocido",
            "stockActual": prod.inventario.cantidadDisponible if prod and prod.inventario else 0,
            "cantidad": d.cantidad,
            "costoUnitario": float(d.costoUnitario),
            "precioLista": float(prod.precioLista or 0.0),
            "subtotal": float(d.subtotal),
            "contexto": "",
            "sugerencia": 0
        })
        
    return {
        "borrador": {
            "idCompra": borrador.idCompra,
            "idProveedor": borrador.idProveedor,
            "montoTotal": float(borrador.montoTotal),
            "items": items
        }
    }

@router.put("/planificacion/borrador")
def sincronizar_borrador(payload: SyncBorradorPayload, id_usuario: int = 1, db: Session = Depends(get_db_session)):
    borrador = db.query(Compra).filter(Compra.estado == "Borrador", Compra.idUsuario == id_usuario).first()
    
    # Validar o asignar proveedor válido si idProveedor es 0
    id_prov = payload.idProveedor
    if not id_prov or id_prov <= 0:
        prov_defecto = db.query(Proveedor).filter(Proveedor.estado == 'ACTIVO').first()
        if prov_defecto:
            id_prov = prov_defecto.idProveedor
        else:
            raise HTTPException(status_code=400, detail="Debe existir al menos un proveedor activo")

    try:
        if borrador:
            borrador.idProveedor = id_prov
            borrador.montoTotal = Decimal(str(payload.montoTotal))
            # Delete old details
            for d in borrador.detalles:
                db.delete(d)
        else:
            borrador = Compra(
                idProveedor=id_prov,
                idUsuario=id_usuario,
                montoTotal=Decimal(str(payload.montoTotal)),
                estado="Borrador"
            )
            db.add(borrador)
            
        db.flush()
        
        # Add new details
        for item in payload.items:
            detalle = DetalleCompra(
                idCompra=borrador.idCompra,
                idProducto=item.idProducto,
                cantidad=item.cantidad,
                costoUnitario=Decimal(str(item.costoUnitario)),
                subtotal=Decimal(str(item.cantidad * item.costoUnitario))
            )
            db.add(detalle)
            
        db.commit()
        return {"status": "success", "idCompra": borrador.idCompra}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ordenes_activas")
def obtener_ordenes_activas(db: Session = Depends(get_db_session)):
    ordenes = db.query(Compra).filter(Compra.estado.in_(["Emitida", "Enviada", "Confirmada", "Recepción parcial"])).order_by(Compra.fechaCompra.desc()).all()
    resultado = []
    for o in ordenes:
        prov = o.proveedor
        resultado.append({
            "idCompra": o.idCompra,
            "proveedor": prov.nombreRazonSocial if prov else "Desconocido",
            "estado": o.estado,
            "fecha": o.fechaCompra.isoformat(),
            "montoTotal": float(o.montoTotal)
        })
    return {"ordenes": resultado}

@router.post("/planificacion/borrador/{id_compra}/consolidar")
def consolidar_orden(id_compra: int, db: Session = Depends(get_db_session)):
    borrador = db.query(Compra).filter(Compra.idCompra == id_compra, Compra.estado == "Borrador").with_for_update().first()
    if not borrador:
        raise HTTPException(status_code=404, detail="Borrador no encontrado o ya consolidado")
        
    if not borrador.detalles:
        raise HTTPException(status_code=400, detail="El borrador no puede estar vacío")
        
    try:
        borrador.estado = "Emitida"
        db.commit()
        
        # TODO PENDIENTE: Disparar worker o evento para notificar al proveedor (Email/WhatsApp) o integración ERP
        # despachar_orden_proveedor(borrador.idCompra)
        
        return {"status": "success", "idCompra": borrador.idCompra, "estado": borrador.estado}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/historial")
def obtener_historial_global(db: Session = Depends(get_db_session)):
    compras = db.query(Compra).filter(Compra.estado == "Completada").order_by(Compra.fechaCompra.desc()).limit(20).all()
    resultado = []
    for compra in compras:
        prov = compra.proveedor
        resultado.append({
            "idCompra": compra.idCompra,
            "proveedor": prov.nombreRazonSocial if prov else "Desconocido",
            "estado": compra.estado,
            "fecha": compra.fechaCompra.isoformat(),
            "montoTotal": float(compra.montoTotal)
        })
    return {"historial": resultado}

@router.get("/historial/{id_compra}/detalles")
def obtener_detalles_compra(id_compra: int, db: Session = Depends(get_db_session)):
    compra = db.query(Compra).filter(Compra.idCompra == id_compra).first()
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    detalles = []
    for d in compra.detalles:
        prod = d.producto
        detalles.append({
            "producto": prod.nombre if prod else "Desconocido",
            "codigo": prod.codigoBarras if prod else "-",
            "cantidad": d.cantidad,
            "costoUnitario": float(d.costoUnitario),
            "subtotal": float(d.subtotal)
        })
    
    return {
        "idCompra": compra.idCompra,
        "fecha": compra.fechaCompra.isoformat(),
        "proveedor": compra.proveedor.nombreRazonSocial if compra.proveedor else "Desconocido",
        "detalles": detalles,
        "montoTotal": float(compra.montoTotal)
    }

@router.get("/historial_producto/{id_producto}")
def obtener_historial_producto(id_producto: int, db: Session = Depends(get_db_session)):
    detalles = db.query(DetalleCompra).filter(DetalleCompra.idProducto == id_producto).join(Compra).order_by(Compra.fechaCompra.desc()).limit(5).all()
    resultado = []
    for d in detalles:
        compra = d.compra
        prov = compra.proveedor
        resultado.append({
            "idCompra": compra.idCompra,
            "proveedor": prov.nombreRazonSocial if prov else "Desconocido",
            "estado": compra.estado,
            "fecha": compra.fechaCompra.isoformat(),
            "cantidad": d.cantidad
        })
    return {"historial": resultado}
