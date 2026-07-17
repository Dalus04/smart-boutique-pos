import datetime
from decimal import Decimal
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from models.catalogo import Categoria, Producto
from models.suministro import Inventario
from models.pos import Venta, DetalleVenta

class AnaliticaService:
    @staticmethod
    def obtener_salud_inventario(db: Session) -> dict:
        """
        Retorna la cantidad de productos y unidades totales agrupados por su estado_stock:
        - Crítico (<= 5)
        - Bajo (<= 15)
        - Óptimo (> 15)
        """
        stmt = (
            select(
                case(
                    (Inventario.cantidadDisponible <= 5, "Crítico"),
                    (Inventario.cantidadDisponible <= 15, "Bajo"),
                    else_="Óptimo"
                ).label("estado"),
                func.count(Inventario.idInventario).label("total_items"),
                func.sum(Inventario.cantidadDisponible).label("total_unidades")
            )
            .group_by("estado")
        )
        results = db.execute(stmt).all()
        
        # Estructura inicial por defecto
        ret = {
            "Crítico": {"items": 0, "unidades": 0},
            "Bajo": {"items": 0, "unidades": 0},
            "Óptimo": {"items": 0, "unidades": 0}
        }
        for estado, items, unidades in results:
            ret[estado] = {"items": items, "unidades": int(unidades or 0)}
        return ret

    @staticmethod
    def obtener_rentabilidad_por_categoria(db: Session) -> list:
        """
        Retorna el margen promedio ponderado para cada categoría:
        ((precio_total - costo_total) / precio_total) * 100
        """
        stmt = (
            select(
                Categoria.nombreCategoria,
                func.sum(Producto.costoProducto).label("costo_total"),
                func.sum(Producto.precioLista).label("precio_total")
            )
            .join(Producto, Categoria.idCategoria == Producto.idCategoria)
            .group_by(Categoria.idCategoria, Categoria.nombreCategoria)
        )
        results = db.execute(stmt).all()
        
        kpis = []
        for nombre_cat, costo, precio in results:
            costo = costo or Decimal("0")
            precio = precio or Decimal("0")
            
            if precio == Decimal("0"):
                margen = 0.0
            else:
                margen = float(((precio - costo) / precio) * 100)
            
            kpis.append({
                "categoria": nombre_cat,
                "costo_total": float(costo),
                "precio_total": float(precio),
                "margen_ponderado": round(margen, 2)
            })
        return kpis

    @staticmethod
    def obtener_tendencia_ventas(db: Session, fecha_inicio: datetime.date = None, fecha_fin: datetime.date = None) -> list:
        """
        Retorna el monto total vendido y cantidad de transacciones agrupado por mes (formato YYYY-MM).
        """
        # Para ser compatible tanto en MySQL como en otros entornos, usamos la función DATE_FORMAT
        mes_expr = func.date_format(Venta.fechaVenta, "%Y-%m").label("mes")
        
        stmt = select(
            mes_expr,
            func.sum(Venta.montoTotal).label("total_vendido"),
            func.count(Venta.idVenta).label("transacciones")
        )
        
        if fecha_inicio:
            stmt = stmt.where(Venta.fechaVenta >= fecha_inicio)
        if fecha_fin:
            stmt = stmt.where(Venta.fechaVenta <= fecha_fin)
            
        stmt = stmt.group_by("mes").order_by("mes")
        results = db.execute(stmt).all()
        
        tendencia = []
        for mes, total, transacciones in results:
            tendencia.append({
                "mes": mes,
                "total_vendido": float(total or 0),
                "transacciones": transacciones
            })
        return tendencia

    @staticmethod
    def obtener_ranking_productos(db: Session, limit: int = 5, fecha_inicio: datetime.date = None, fecha_fin: datetime.date = None) -> list:
        """
        Retorna el top N de productos más vendidos ordenados por cantidad.
        """
        stmt = (
            select(
                Producto.idProducto,
                Producto.nombre,
                func.sum(DetalleVenta.cantidad).label("cantidad_vendida"),
                func.sum(DetalleVenta.subtotal).label("total_recaudado")
            )
            .join(DetalleVenta, Producto.idProducto == DetalleVenta.idProducto)
            .join(Venta, Venta.idVenta == DetalleVenta.idVenta)
        )
        
        if fecha_inicio:
            stmt = stmt.where(Venta.fechaVenta >= fecha_inicio)
        if fecha_fin:
            stmt = stmt.where(Venta.fechaVenta <= fecha_fin)
            
        stmt = stmt.group_by(Producto.idProducto, Producto.nombre).order_by(func.sum(DetalleVenta.cantidad).desc()).limit(limit)
        results = db.execute(stmt).all()
        
        ranking = []
        for id_prod, nombre, cantidad, monto in results:
            ranking.append({
                "idProducto": id_prod,
                "nombre": nombre,
                "cantidad_vendida": int(cantidad or 0),
                "total_recaudado": float(monto or 0)
            })
        return ranking
