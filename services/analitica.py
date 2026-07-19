import datetime
from decimal import Decimal
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from models.catalogo import Categoria, Producto
from models.suministro import Inventario
from models.pos import Venta, DetalleVenta
from models.actores import Cliente

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
                func.count(Inventario.idProducto).label("total_items"),
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

    @staticmethod
    def obtener_metricas_completas(db: Session, periodo: str = "7_dias") -> dict:
        now = datetime.datetime.now()
        
        # Calcular rangos
        if periodo == "mes":
            dias_t0 = 30
        elif periodo == "anio":
            dias_t0 = 365
        elif periodo == "hoy":
            dias_t0 = 1
        else:
            dias_t0 = 7
            
        fin_t0 = now
        inicio_t0 = fin_t0 - datetime.timedelta(days=dias_t0)
        
        fin_t1 = inicio_t0
        inicio_t1 = fin_t1 - datetime.timedelta(days=dias_t0)
        
        # Helpers
        def get_ventas(ini, fin):
            stmt = select(func.sum(Venta.montoTotal), func.count(Venta.idVenta)).where(Venta.fechaVenta >= ini, Venta.fechaVenta <= fin)
            return db.execute(stmt).first()
            
        def get_utilidad(ini, fin):
            stmt = select(
                func.sum((DetalleVenta.precioUnitario - DetalleVenta.costoUnitario) * DetalleVenta.cantidad)
            ).join(Venta, Venta.idVenta == DetalleVenta.idVenta).where(
                Venta.fechaVenta >= ini, Venta.fechaVenta <= fin
            )
            return db.execute(stmt).scalar() or Decimal("0")
            
        def get_clientes(ini, fin):
            stmt = select(func.count(func.distinct(Venta.idCliente))).where(Venta.fechaVenta >= ini, Venta.fechaVenta <= fin)
            return db.execute(stmt).scalar() or 0

        # T0 metrics
        ventas_t0, count_t0 = get_ventas(inicio_t0, fin_t0)
        ventas_t0 = float(ventas_t0 or 0)
        utilidad_t0 = float(get_utilidad(inicio_t0, fin_t0))
        clientes_t0 = get_clientes(inicio_t0, fin_t0)
        
        # T1 metrics
        ventas_t1, _ = get_ventas(inicio_t1, fin_t1)
        ventas_t1 = float(ventas_t1 or 0)
        utilidad_t1 = float(get_utilidad(inicio_t1, fin_t1))
        clientes_t1 = get_clientes(inicio_t1, fin_t1)
        
        # Variations
        def calc_var(t0, t1):
            if t1 == 0:
                return 100.0 if t0 > 0 else 0.0
            return ((t0 - t1) / t1) * 100.0
            
        # Margen Bruto
        margen_t0 = (utilidad_t0 / ventas_t0 * 100) if ventas_t0 > 0 else 0
        margen_t1 = (utilidad_t1 / ventas_t1 * 100) if ventas_t1 > 0 else 0
        
        # Obtener inventario actual
        salud = AnaliticaService.obtener_salud_inventario(db)
        
        # Chart data for T0
        tendencia_t0 = AnaliticaService.obtener_tendencia_ventas(db, inicio_t0.date(), fin_t0.date())
        ranking_t0 = AnaliticaService.obtener_ranking_productos(db, 5, inicio_t0.date(), fin_t0.date())
        categorias_t0 = AnaliticaService.obtener_rentabilidad_por_categoria(db) 
        
        return {
            "kpis": {
                "ventas": {"valor": ventas_t0, "var": calc_var(ventas_t0, ventas_t1)},
                "utilidad": {"valor": utilidad_t0, "var": calc_var(utilidad_t0, utilidad_t1)},
                "clientes": {"valor": clientes_t0, "var": calc_var(clientes_t0, clientes_t1)},
                "margen": {"valor": margen_t0, "var": margen_t0 - margen_t1} # Variación en puntos porcentuales
            },
            "charts": {
                "tendencia": tendencia_t0,
                "ranking": ranking_t0,
                "categorias": categorias_t0
            },
            "salud_inventario": salud,
            "proyeccion_mes": AnaliticaService.proyectar_ventas_mes(db)
        }

    @staticmethod
    def proyectar_ventas_mes(db: Session) -> float:
        import calendar
        now = datetime.datetime.now()
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        stmt = select(func.sum(Venta.montoTotal)).where(
            Venta.fechaVenta >= inicio_mes,
            Venta.fechaVenta <= now
        )
        ventas_actuales = db.execute(stmt).scalar() or Decimal("0")
        ventas_actuales = float(ventas_actuales)
        
        dia_actual = now.day
        _, dias_del_mes = calendar.monthrange(now.year, now.month)
        
        if dia_actual == 0: return 0.0
        return (ventas_actuales / dia_actual) * dias_del_mes
