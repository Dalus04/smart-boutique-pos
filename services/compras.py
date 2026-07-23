from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.suministro import Compra, DetalleCompra, Inventario, SolicitudReposicion
from models.catalogo import Producto
from models.actores import Proveedor
from services.prediccion import PrediccionService

class ComprasService:
    @staticmethod
    def obtener_sugerencias_compra(db: Session):
        productos_activos = db.query(Producto).filter(Producto.estado == 'ACTIVO').all()
        
        sugerencias = []
        for prod in productos_activos:
            reporte = PrediccionService.evaluar_producto(db, prod.idProducto, dias_entrega=7)
            
            velocidad = reporte["velocidad_venta_diaria"]
            stock_actual = reporte["stock_actual"]
            riesgo = reporte["riesgo"]
            
            sugerencia_compra = max(0, int((velocidad * 30) - stock_actual))
            
            if sugerencia_compra > 0 and riesgo in ["Riesgo Alto", "Riesgo Medio", "Crítico"]:
                contexto = "Alta rotación. Riesgo de quiebre inminente." if velocidad > 1 else "Stock bajo. Reposición preventiva."
                    
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
                    "prioridad": sugerencia_compra * velocidad
                })
                
        sugerencias.sort(key=lambda x: x["prioridad"], reverse=True)
        sugerencias = sugerencias[:5]
        
        proveedor_sugerido = db.query(Proveedor).filter(Proveedor.estado == 'ACTIVO').first()
        
        return {
            "proveedorSugerido": proveedor_sugerido.idProveedor if proveedor_sugerido else None,
            "sugerencias": sugerencias
        }

    @staticmethod
    def crear_solicitud(db: Session, payload):
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

    @staticmethod
    def obtener_solicitudes_pendientes(db: Session):
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

    @staticmethod
    def registrar_compra(db: Session, payload, id_usuario: int):
        if not payload.items:
            raise HTTPException(status_code=400, detail="La orden de compra no puede estar vacía")
            
        try:
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

    @staticmethod
    def cambiar_estado_compra(db: Session, id_compra: int, payload):
        compra = db.query(Compra).filter(Compra.idCompra == id_compra).with_for_update().first()
        if not compra:
            raise HTTPException(status_code=404, detail="Compra no encontrada")
            
        estados_validos = ["Borrador", "Emitida", "Enviada", "Confirmada", "Recepción parcial", "Completada", "Cancelada"]
        if payload.estado not in estados_validos:
            raise HTTPException(status_code=400, detail="Estado inválido")
            
        stock_actualizado = []
        
        if payload.estado == "Completada" and compra.estado != "Completada":
            try:
                with db.begin_nested():
                    for detalle in compra.detalles:
                        inventario = db.query(Inventario).filter(Inventario.idProducto == detalle.idProducto).with_for_update().first()
                        if inventario:
                            inventario.cantidadDisponible += detalle.cantidad
                        else:
                            inventario = Inventario(idProducto=detalle.idProducto, cantidadDisponible=detalle.cantidad)
                            db.add(inventario)
                        
                        producto = db.query(Producto).filter(Producto.idProducto == detalle.idProducto).first()
                        if producto:
                            producto.costoProducto = detalle.costoUnitario

                        solicitudes = db.query(SolicitudReposicion).filter(
                            SolicitudReposicion.idProducto == detalle.idProducto,
                            SolicitudReposicion.estado == "Pendiente"
                        ).all()
                        for sol in solicitudes:
                            sol.estado = "Agregada"

                        prod_nombre = producto.nombre if producto else f"Producto #{detalle.idProducto}"
                        stock_actualizado.append({
                            "producto": prod_nombre,
                            "stock": inventario.cantidadDisponible
                        })

            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Error en transacción atómica: {str(e)}")

        compra.estado = payload.estado
        db.commit()
        return {
            "status": "success", 
            "nuevo_estado": compra.estado,
            "message": "Orden recibida",
            "stock_actualizado": stock_actualizado
        }

    @staticmethod
    def obtener_borrador_activo(db: Session, id_usuario: int):
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

    @staticmethod
    def sincronizar_borrador(db: Session, payload, id_usuario: int):
        borrador = db.query(Compra).filter(Compra.estado == "Borrador", Compra.idUsuario == id_usuario).first()
        
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

    @staticmethod
    def obtener_ordenes_activas(db: Session):
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

    @staticmethod
    def consolidar_orden(db: Session, id_compra: int):
        borrador = db.query(Compra).filter(Compra.idCompra == id_compra, Compra.estado == "Borrador").with_for_update().first()
        if not borrador:
            raise HTTPException(status_code=404, detail="Borrador no encontrado o ya consolidado")
            
        if not borrador.detalles:
            raise HTTPException(status_code=400, detail="El borrador no puede estar vacío")
            
        try:
            borrador.estado = "Emitida"
            db.commit()
            return {"status": "success", "idCompra": borrador.idCompra, "estado": borrador.estado}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def obtener_historial_global(db: Session):
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

    @staticmethod
    def obtener_detalles_compra(db: Session, id_compra: int):
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

    @staticmethod
    def obtener_historial_producto(db: Session, id_producto: int):
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
