import datetime
import calendar
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
            "Bajo":    {"items": 0, "unidades": 0},
            "Óptimo":  {"items": 0, "unidades": 0}
        }
        for estado, items, unidades in results:
            ret[estado] = {"items": items, "unidades": int(unidades or 0)}
        return ret

    @staticmethod
    def calcular_health_score(kpis: dict, salud_inventario: dict) -> dict:
        """
        Calcula el score de salud del negocio (0-100) en el servidor.
        Retorna score, estado textual y lista de factores para el modal.
        """
        score = 0
        criticos = (salud_inventario.get("Crítico") or {}).get("items", 0)
        bajos    = (salud_inventario.get("Bajo")    or {}).get("items", 0)

        # Factor 1 — Utilidad positiva (+30)
        utilidad_positiva = kpis["utilidad"]["valor"] > 0
        if utilidad_positiva:
            score += 30

        # Factor 2 — Ventas en crecimiento (+30)
        ventas_crecen = kpis["ventas"]["var"] >= 0
        if ventas_crecen:
            score += 30

        # Factor 3 — Stock crítico (+40 / +20 / +0)
        if criticos == 0:
            score += 40
            stock_label = "Sin productos en stock crítico"
            stock_pts   = "+40 pts"
            stock_ok    = True
        elif criticos <= 5:
            score += 20
            stock_label = f"{criticos} producto(s) en stock crítico (riesgo moderado)"
            stock_pts   = "+20 pts"
            stock_ok    = False
        else:
            stock_label = f"{criticos} productos en stock crítico"
            stock_pts   = "+0 pts"
            stock_ok    = False

        # Estado textual
        if score >= 80:
            estado = "Excelente"
        elif score >= 50:
            estado = "Regular"
        else:
            estado = "Atención Requerida"

        factores = [
            {
                "label": "Utilidad positiva en el período",
                "ok":    utilidad_positiva,
                "pts":   "+30 pts"
            },
            {
                "label": "Ventas en crecimiento vs período anterior",
                "ok":    ventas_crecen,
                "pts":   "+30 pts"
            },
            {
                "label": stock_label,
                "ok":    stock_ok,
                "pts":   stock_pts
            },
        ]

        # Contexto informativo (sin impacto en score)
        contexto = [
            {
                "warn":  bajos > 0,
                "label": f"{bajos} producto(s) con stock bajo (≤ 15 unidades)"
                         if bajos > 0
                         else "Todos los productos tienen stock saludable"
            },
        ]

        return {
            "score":    score,
            "estado":   estado,
            "factores": factores,
            "contexto": contexto,
        }

    # ── Regresión lineal simple (OLS) ─────────────────────────────────────
    @staticmethod
    def _regresion_lineal(valores: list[float]) -> list[float]:
        """
        Calcula la línea de tendencia (OLS) para una serie de valores.
        Retorna un array del mismo tamaño con los valores proyectados.
        """
        n = len(valores)
        if n < 2:
            return list(valores)

        sum_x  = sum(range(n))
        sum_y  = sum(valores)
        sum_xy = sum(i * y for i, y in enumerate(valores))
        sum_xx = sum(i * i for i in range(n))

        denom = n * sum_xx - sum_x ** 2
        if denom == 0:
            return list(valores)

        slope     = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        return [round(intercept + slope * i, 2) for i in range(n)]

    @staticmethod
    def obtener_rentabilidad_por_categoria(db: Session, fecha_inicio: datetime.date = None, fecha_fin: datetime.date = None) -> list:
        """
        Retorna el margen promedio ponderado para cada categoría basado en ventas reales:
        ((precio_total - costo_total) / precio_total) * 100
        """
        stmt = (
            select(
                Categoria.nombreCategoria,
                func.sum(DetalleVenta.costoUnitario * DetalleVenta.cantidad).label("costo_total"),
                func.sum(DetalleVenta.subtotal).label("precio_total")
            )
            .join(Producto, Categoria.idCategoria == Producto.idCategoria)
            .join(DetalleVenta, Producto.idProducto == DetalleVenta.idProducto)
            .join(Venta, Venta.idVenta == DetalleVenta.idVenta)
        )

        if fecha_inicio:
            stmt = stmt.where(Venta.fechaVenta >= fecha_inicio)
        if fecha_fin:
            stmt = stmt.where(Venta.fechaVenta <= fecha_fin)

        stmt = stmt.group_by(Categoria.idCategoria, Categoria.nombreCategoria)
        results = db.execute(stmt).all()

        kpis = []
        for nombre_cat, costo, precio in results:
            costo  = costo  or Decimal("0")
            precio = precio or Decimal("0")

            if precio == Decimal("0"):
                margen = 0.0
            else:
                margen = float(((precio - costo) / precio) * 100)

            kpis.append({
                "categoria":        nombre_cat,
                "costo_total":      float(costo),
                "precio_total":     float(precio),
                "margen_ponderado": round(margen, 2)
            })
        return kpis

    @staticmethod
    def obtener_tendencia_ventas(db: Session, fecha_inicio: datetime.date = None, fecha_fin: datetime.date = None) -> list:
        """
        Retorna el monto total vendido y cantidad de transacciones agrupado por mes (formato YYYY-MM).
        """
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
                "mes":          mes,
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
                "idProducto":     id_prod,
                "nombre":         nombre,
                "cantidad_vendida": int(cantidad or 0),
                "total_recaudado":  float(monto or 0)
            })
        return ranking

    @staticmethod
    def obtener_metricas_completas(
        db: Session,
        periodo: str = "7_dias",
        fecha_inicio_custom: datetime.date = None,
        fecha_fin_custom: datetime.date = None
    ) -> dict:
        now = datetime.datetime.now()

        if fecha_inicio_custom and fecha_fin_custom:
            inicio_t0 = datetime.datetime.combine(fecha_inicio_custom, datetime.time.min)
            fin_t0    = datetime.datetime.combine(fecha_fin_custom, datetime.time.max)
            dias_t0   = max((fin_t0 - inicio_t0).days, 1)
        elif periodo == "todo":
            # Obtener la fecha de la primera venta registrada en la base de datos
            min_fecha = db.execute(select(func.min(Venta.fechaVenta))).scalar()
            inicio_t0 = min_fecha if min_fecha else now - datetime.timedelta(days=365)
            fin_t0    = now
            dias_t0   = max((fin_t0 - inicio_t0).days, 1)
        elif periodo == "mes":
            dias_t0   = 30
            fin_t0    = now
            inicio_t0 = fin_t0 - datetime.timedelta(days=dias_t0)
        elif periodo == "anio":
            dias_t0   = 365
            fin_t0    = now
            inicio_t0 = fin_t0 - datetime.timedelta(days=dias_t0)
        elif periodo == "hoy":
            dias_t0   = 1
            fin_t0    = now
            inicio_t0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # 7_dias
            dias_t0   = 7
            fin_t0    = now
            inicio_t0 = fin_t0 - datetime.timedelta(days=dias_t0)

        fin_t1   = inicio_t0
        inicio_t1 = fin_t1 - datetime.timedelta(days=dias_t0)

        # Helpers SQL
        def get_ventas(ini, fin):
            stmt = select(func.sum(Venta.montoTotal), func.count(Venta.idVenta)).where(
                Venta.fechaVenta >= ini, Venta.fechaVenta <= fin
            )
            return db.execute(stmt).first()

        def get_utilidad(ini, fin):
            stmt = select(
                func.sum((DetalleVenta.precioUnitario - DetalleVenta.costoUnitario) * DetalleVenta.cantidad)
            ).join(Venta, Venta.idVenta == DetalleVenta.idVenta).where(
                Venta.fechaVenta >= ini, Venta.fechaVenta <= fin
            )
            return db.execute(stmt).scalar() or Decimal("0")

        def get_clientes(ini, fin):
            stmt = select(func.count(func.distinct(Venta.idCliente))).where(
                Venta.fechaVenta >= ini, Venta.fechaVenta <= fin
            )
            return db.execute(stmt).scalar() or 0

        # Métricas período actual (T0)
        ventas_t0, count_t0 = get_ventas(inicio_t0, fin_t0)
        ventas_t0   = float(ventas_t0 or 0)
        utilidad_t0 = float(get_utilidad(inicio_t0, fin_t0))
        clientes_t0 = get_clientes(inicio_t0, fin_t0)

        # Métricas período anterior (T1)
        ventas_t1, _ = get_ventas(inicio_t1, fin_t1)
        ventas_t1   = float(ventas_t1 or 0)
        utilidad_t1 = float(get_utilidad(inicio_t1, fin_t1))
        clientes_t1 = get_clientes(inicio_t1, fin_t1)

        # Variaciones porcentuales
        def calc_var(t0, t1):
            if t1 == 0:
                return 100.0 if t0 > 0 else 0.0
            return round(((t0 - t1) / t1) * 100.0, 2)

        # Márgenes
        margen_t0 = (utilidad_t0 / ventas_t0 * 100) if ventas_t0 > 0 else 0.0
        margen_t1 = (utilidad_t1 / ventas_t1 * 100) if ventas_t1 > 0 else 0.0

        kpis = {
            "ventas":   {"valor": ventas_t0,   "var": calc_var(ventas_t0,   ventas_t1)},
            "utilidad": {"valor": utilidad_t0,  "var": calc_var(utilidad_t0, utilidad_t1)},
            "clientes": {"valor": clientes_t0,  "var": calc_var(clientes_t0, clientes_t1)},
            "margen":   {"valor": round(margen_t0, 2), "var": round(margen_t0 - margen_t1, 2)},
        }

        # Inventario
        salud = AnaliticaService.obtener_salud_inventario(db)

        # Health score — calculado en servidor
        health = AnaliticaService.calcular_health_score(kpis, salud)

        # Datos de gráficos para T0
        tendencia_t0  = AnaliticaService.obtener_tendencia_ventas(db, inicio_t0.date(), fin_t0.date())
        ranking_t0    = AnaliticaService.obtener_ranking_productos(db, 5, inicio_t0.date(), fin_t0.date())
        categorias_t0 = AnaliticaService.obtener_rentabilidad_por_categoria(db, inicio_t0.date(), fin_t0.date())

        # Línea de regresión lineal calculada en servidor
        valores_tendencia = [p["total_vendido"] for p in tendencia_t0]
        tendencia_regresion = AnaliticaService._regresion_lineal(valores_tendencia)

        # Proyección al fin de mes (siempre sobre el mes calendar actual)
        proyeccion_fin_mes = AnaliticaService.proyectar_ventas_mes(db)

        return {
            "kpis":             kpis,
            "health":           health,
            "charts": {
                "tendencia":            tendencia_t0,
                "tendencia_regresion":  tendencia_regresion,
                "ranking":              ranking_t0,
                "categorias":           categorias_t0,
            },
            "salud_inventario":  salud,
            # Retrocompatibilidad — se mantiene el nombre antiguo
            "proyeccion_mes":    proyeccion_fin_mes,
            "proyeccion_fin_mes": proyeccion_fin_mes,
        }

    @staticmethod
    def proyectar_ventas_mes(db: Session) -> float:
        """
        Proyecta las ventas totales al cierre del mes actual usando
        el ritmo diario promedio del mes en curso.
        """
        now = datetime.datetime.now()
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stmt = select(func.sum(Venta.montoTotal)).where(
            Venta.fechaVenta >= inicio_mes,
            Venta.fechaVenta <= now
        )
        ventas_actuales = float(db.execute(stmt).scalar() or Decimal("0"))

        dia_actual   = now.day
        _, dias_del_mes = calendar.monthrange(now.year, now.month)

        if dia_actual == 0:
            return 0.0
        return round((ventas_actuales / dia_actual) * dias_del_mes, 2)
