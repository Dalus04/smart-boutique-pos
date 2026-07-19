from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

from api.dependencies import get_db_session
from models.catalogo import Producto
from models.suministro import Inventario
from models.pos import Venta, DetalleVenta, Pago, MedioPago
from models.actores import Cliente
from services.mineria import MineriaService
from services.asistente import AsistenteComercialService
from sqlalchemy import func

router = APIRouter(
    prefix="/api/v1/pos",
    tags=["POS"]
)

# Schemas
class CartItem(BaseModel):
    idProducto: int
    cantidad: int
    precioUnitario: float
    costoUnitario: float
    
class CheckoutPayload(BaseModel):
    items: List[CartItem]
    idMedioPago: int
    montoTotal: float
    # idCliente es opcional (Ventas Rápidas)
    idCliente: Optional[int] = None

class ContextoPayload(BaseModel):
    carrito_ids: List[int] = []
    idCliente: Optional[int] = None

@router.get("/productos")
def buscar_productos(
    q: Optional[str] = Query(None, description="Búsqueda por código, nombre o ID"),
    db: Session = Depends(get_db_session)
):
    query = db.query(Producto).filter(Producto.estado == 'ACTIVO')
    
    if q:
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
    q: Optional[str] = Query(None, description="Búsqueda por DNI o nombre"),
    db: Session = Depends(get_db_session)
):
    query = db.query(Cliente).filter(Cliente.estado == 'ACTIVO')
    
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Cliente.numeroDocumento == q,
                Cliente.nombres.ilike(search_term),
                Cliente.apellidos.ilike(search_term)
            )
        )
        
    clientes = query.limit(10).all()
    
    resultados = []
    for c in clientes:
        resultados.append(AsistenteComercialService.analizar_cliente(db, c.idCliente))
        
    return resultados

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
        
    id_usuario = 1 # Hardcodeado temporalmente por requerimiento de Fase 3
    
    try:
        # 1. Validar Stock y descontar (Transaccional)
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
            "utilidad_total": utilidad_total
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error procesando la venta: {str(e)}")
