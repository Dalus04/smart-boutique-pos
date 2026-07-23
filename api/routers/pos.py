import math
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

from api.dependencies import get_db_session, obtener_id_usuario_defecto
from api.schemas.pos import (
    CartItem,
    CheckoutPayload,
    ContextoPayload,
    QuickClientePayload,
)
from models.catalogo import Producto, Categoria
from models.suministro import Inventario
from models.pos import Venta, DetalleVenta, Pago, MedioPago
from models.actores import Cliente
from services.mineria import MineriaService
from services.asistente import AsistenteComercialService

router = APIRouter(
    prefix="/api/v1/pos",
    tags=["POS"]
)

@router.get("/productos")
def buscar_productos(
    q: Optional[str] = Query(None, description="Búsqueda por código, nombre o ID"),
    categoria: Optional[int] = Query(None, description="Filtro por ID de categoría"),
    db: Session = Depends(get_db_session)
):
    query = db.query(Producto).filter(Producto.estado == 'ACTIVO')
    
    cat_id = categoria if isinstance(categoria, int) else None
    if cat_id:
        query = query.filter(Producto.idCategoria == cat_id)
    
    if q and isinstance(q, str):
        search_term = f"%{q}%"
        id_filter = []
        if q.isdigit():
            id_filter.append(Producto.idProducto == int(q))
            
        query = query.filter(
            or_(
                Producto.codigoBarras == q,
                Producto.nombre.ilike(search_term),
                *id_filter
            )
        )
        
    productos = query.limit(20).all()
    
    resultados = []
    for p in productos:
        if p.inventario and p.inventario.cantidadDisponible > 0:
            salud = AsistenteComercialService.evaluar_salud_producto(p)
            resultados.append(salud)
            
    return resultados


@router.get("/clientes")
def buscar_clientes(
    q: Optional[str] = Query(None, description="Búsqueda por DNI, Nombre o Apellido"),
    db: Session = Depends(get_db_session)
):
    query = db.query(Cliente).filter(Cliente.estado == 'ACTIVO')
    
    if q and isinstance(q, str):
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Cliente.numeroDocumento.ilike(search_term),
                Cliente.nombres.ilike(search_term),
                Cliente.apellidos.ilike(search_term),
                func.concat(Cliente.nombres, ' ', Cliente.apellidos).ilike(search_term),
                func.concat(Cliente.apellidos, ' ', Cliente.nombres).ilike(search_term)
            )
        )
        
    clientes = query.limit(10).all()
    
    resultados = []
    for c in clientes:
        resultados.append(AsistenteComercialService.analizar_cliente(db, c.idCliente))
        
    return resultados

@router.post("/clientes")
def registrar_cliente_rapido(
    payload: QuickClientePayload,
    db: Session = Depends(get_db_session)
):
    dni = payload.numeroDocumento.strip()
    nombres = payload.nombres.strip()
    apellidos = payload.apellidos.strip()
    
    if not dni or not nombres or not apellidos:
        raise HTTPException(status_code=400, detail="DNI, Nombres y Apellidos son obligatorios")
        
    # Verificar si existe por DNI
    existente = db.query(Cliente).filter(Cliente.numeroDocumento == dni).first()
    if existente:
        # Si ya existe, lo retornamos directo
        return AsistenteComercialService.analizar_cliente(db, existente.idCliente)
        
    nuevo_cliente = Cliente(
        tipoDocumento="DNI",
        numeroDocumento=dni,
        nombres=nombres,
        apellidos=apellidos,
        estado="ACTIVO"
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    
    return AsistenteComercialService.analizar_cliente(db, nuevo_cliente.idCliente)

@router.get("/medios-pago")
def get_medios_pago(db: Session = Depends(get_db_session)):
    medios = db.query(MedioPago).filter(MedioPago.estado == 'ACTIVO').all()
    return [{"id": m.idMedioPago, "nombre": m.nombreMedioPago} for m in medios]

@router.post("/analizar-ticket")
def analizar_ticket(
    payload: ContextoPayload, 
    db: Session = Depends(get_db_session)
):
    """
    Devuelve un contexto comercial completo (cliente, cross_sell, etc.) 
    delegando la inteligencia al AsistenteComercialService.
    """
    return AsistenteComercialService.generar_contexto_comercial(
        db=db, 
        carrito_ids=payload.carrito_ids, 
        id_cliente=payload.idCliente
    )

@router.post("/checkout")
def procesar_checkout(
    payload: CheckoutPayload,
    db: Session = Depends(get_db_session)
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="El carrito está vacío")
        
    id_usuario = obtener_id_usuario_defecto(db)
    
    try:
        # 1. Validar Stock y descontar (Transaccional)
        productos_afectados = []
        for item in payload.items:
            inventario = db.query(Inventario).filter(Inventario.idProducto == item.idProducto).with_for_update().first()
            if not inventario or inventario.cantidadDisponible < item.cantidad:
                db.rollback()
                prod = db.query(Producto).get(item.idProducto)
                raise HTTPException(
                    status_code=400, 
                    detail=f"Stock insuficiente para {prod.nombre if prod else item.idProducto}"
                )
            # Descontar stock
            inventario.cantidadDisponible -= item.cantidad
            prod = db.query(Producto).get(item.idProducto)
            productos_afectados.append({
                "id": item.idProducto,
                "nombre": prod.nombre if prod else f"Producto #{item.idProducto}",
                "stock_actual": inventario.cantidadDisponible
            })

        # 2. Crear Cabecera de Venta
        venta = Venta(
            idCliente=payload.idCliente,
            idUsuario=id_usuario,
            montoTotal=Decimal(str(payload.montoTotal))
        )
        db.add(venta)
        db.flush() # Para obtener el idVenta
        
        # 3. Crear Detalles de Venta y calcular utilidad
        utilidad_total = 0.0
        for item in payload.items:
            util_item = (item.precioUnitario - item.costoUnitario) * item.cantidad
            utilidad_total += util_item
            
            detalle = DetalleVenta(
                idVenta=venta.idVenta,
                idProducto=item.idProducto,
                cantidad=item.cantidad,
                costoUnitario=Decimal(str(item.costoUnitario)),
                precioUnitario=Decimal(str(item.precioUnitario)),
                subtotal=Decimal(str(item.cantidad * item.precioUnitario))
            )
            db.add(detalle)
            
        # 4. Registrar Pago
        pago = Pago(
            idVenta=venta.idVenta,
            idMedioPago=payload.idMedioPago,
            montoPagado=Decimal(str(payload.montoTotal))
        )
        db.add(pago)
        
        # 5. Commit Transaccional
        db.commit()
        
        return {
            "status": "success", 
            "idVenta": venta.idVenta, 
            "mensaje": "Venta procesada con éxito",
            "utilidad_total": utilidad_total,
            "productos_afectados": productos_afectados
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error procesando la venta: {str(e)}")

@router.get("/categorias")
def get_categorias(db: Session = Depends(get_db_session)):
    categorias = db.query(Categoria).filter(Categoria.estado == 'ACTIVO').all()
    return [{"id": c.idCategoria, "nombre": c.nombreCategoria} for c in categorias]

@router.get("/historial")
def get_historial(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(10, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db_session)
):
    total_items = db.query(func.count(Venta.idVenta)).scalar() or 0
    pages = math.ceil(total_items / size) if size > 0 else 1
    offset = (page - 1) * size

    ventas = db.query(Venta).order_by(desc(Venta.fechaVenta)).offset(offset).limit(size).all()
    items = []
    for v in ventas:
        cliente_nombre = "Cliente Genérico"
        if v.cliente:
            cliente_nombre = f"{v.cliente.nombres} {v.cliente.apellidos}"
        
        items.append({
            "idVenta": v.idVenta,
            "fecha": v.fechaVenta.isoformat(),
            "cliente": cliente_nombre,
            "montoTotal": float(v.montoTotal),
            "articulos": v.total_articulos,
            "estado": v.estadoVenta
        })
    return {
        "items": items,
        "total_items": total_items,
        "page": page,
        "pages": pages
    }

@router.get("/historial/{id_venta}")
def get_detalle_venta(id_venta: int, db: Session = Depends(get_db_session)):
    venta = db.query(Venta).filter(Venta.idVenta == id_venta).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
        
    cliente_nombre = "Cliente Genérico"
    if venta.cliente:
        cliente_nombre = f"{venta.cliente.nombres} {venta.cliente.apellidos}"
        
    detalles = []
    utilidad_total = 0.0
    for d in venta.detalles:
        subtotal = float(d.subtotal)
        costo_total = float(d.costoUnitario) * d.cantidad
        utilidad_total += (subtotal - costo_total)
        
        detalles.append({
            "idProducto": d.idProducto,
            "nombreProducto": d.producto.nombre if d.producto else f"Producto #{d.idProducto}",
            "cantidad": d.cantidad,
            "precioUnitario": float(d.precioUnitario),
            "subtotal": subtotal
        })
        
    medio_pago = "Efectivo"
    if venta.pagos and len(venta.pagos) > 0 and venta.pagos[0].medio_pago:
        medio_pago = venta.pagos[0].medio_pago.nombreMedioPago
        
    return {
        "idVenta": venta.idVenta,
        "fecha": venta.fechaVenta.isoformat(),
        "cliente": cliente_nombre,
        "montoTotal": float(venta.montoTotal),
        "medioPago": medio_pago,
        "utilidad": utilidad_total,
        "detalles": detalles
    }
