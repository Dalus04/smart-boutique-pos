from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.pos import Venta, DetalleVenta
from models.suministro import Inventario

class PrediccionService:

    @classmethod
    def calcular_velocidad_venta(cls, session: Session, id_producto: int, dias: int = 30) -> float:
        """
        Calcula el promedio de unidades vendidas por día en los últimos 'dias'.
        """
        fecha_limite = date.today() - timedelta(days=dias)
        
        # Uso de func.sum() para sumar la cantidad de productos vendidos en la BD
        total_vendido = session.query(func.sum(DetalleVenta.cantidad)).\
            join(Venta, DetalleVenta.idVenta == Venta.idVenta).\
            filter(DetalleVenta.idProducto == id_producto).\
            filter(Venta.fechaVenta >= fecha_limite).\
            scalar()
            
        if not total_vendido:
            return 0.0
            
        return float(total_vendido) / dias

    @classmethod
    def clasificar_riesgo_quiebre(cls, stock_actual: int, velocidad_venta: float, dias_entrega: int) -> str:
        """
        Clasifica el riesgo de quebrar el stock antes de que llegue el pedido.
        Retorna 'Riesgo Alto', 'Riesgo Medio', o 'Sin Riesgo'.
        """
        demanda_esperada = velocidad_venta * dias_entrega
        
        # Nodo 1: El stock actual no alcanza ni siquiera para cubrir la demanda esperada justa
        if stock_actual <= demanda_esperada:
            return 'Riesgo Alto'
            
        # Nodo 2: El stock cubre la demanda pero no supera el factor de seguridad (50% extra)
        if stock_actual <= demanda_esperada * 1.5:
            return 'Riesgo Medio'
            
        # El stock es superior al margen de seguridad
        return 'Sin Riesgo'

    @classmethod
    def evaluar_producto(cls, session: Session, id_producto: int, dias_entrega: int) -> dict:
        """
        Evalúa el estado completo de riesgo de un producto y retorna un reporte.
        """
        # Sumar la cantidad disponible de todos los registros de inventario para este producto
        stock_actual = session.query(func.sum(Inventario.cantidadDisponible)).\
            filter(Inventario.idProducto == id_producto).\
            scalar()
            
        stock_actual = int(stock_actual) if stock_actual is not None else 0
        
        velocidad = cls.calcular_velocidad_venta(session, id_producto)
        riesgo = cls.clasificar_riesgo_quiebre(stock_actual, velocidad, dias_entrega)
        
        return {
            "id_producto": id_producto,
            "stock_actual": stock_actual,
            "velocidad_venta_diaria": velocidad,
            "dias_entrega": dias_entrega,
            "riesgo": riesgo
        }
