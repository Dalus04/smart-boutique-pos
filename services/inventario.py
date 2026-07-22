"""
InventarioService — Lógica de negocio del módulo de Inventario.

Centraliza: KPIs globales, clasificación ABC (Pareto), estado físico de
stock, contexto semántico de cada producto, heurística de ordenamiento
y operaciones CRUD de catálogo.

Ninguna función de este módulo maneja objetos HTTP (Request, Response,
HTTPException). Eso es responsabilidad exclusiva del router.
"""
import math
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from models.catalogo import Producto, Categoria
from models.suministro import Inventario, SolicitudReposicion
from models.pos import DetalleVenta
from services.prediccion import PrediccionService
from services.mineria import MineriaService
from api.schemas.inventario import CategoriaCreate, ProductoCreate, ProductoUpdate


# ── Thresholds de stock (única fuente de verdad) ─────────────────────────────
STOCK_CRITICO = 5    # <= STOCK_CRITICO → "Crítico"
STOCK_BAJO    = 15   # <= STOCK_BAJO    → "Bajo"
                     # >  STOCK_BAJO    → "Óptimo"


class InventarioService:

    # ── KPIs globales ────────────────────────────────────────────────────────

    @staticmethod
    def get_kpis_globales(db: Session) -> dict:
        """
        Calcula los KPIs del tablero de inventario en una sola pasada SQL.
        Incluye health score y su texto descriptivo.
        """
        productos_activos = (
            db.query(Producto)
            .filter(Producto.estado == "ACTIVO")
            .count()
        )

        stock_total = int(
            db.query(func.coalesce(func.sum(Inventario.cantidadDisponible), 0))
            .join(Producto, Inventario.idProducto == Producto.idProducto)
            .filter(Producto.estado == "ACTIVO")
            .scalar() or 0
        )

        solicitudes_en_proceso = (
            db.query(func.count(func.distinct(SolicitudReposicion.idProducto)))
            .join(Producto, SolicitudReposicion.idProducto == Producto.idProducto)
            .filter(
                Producto.estado == "ACTIVO",
                SolicitudReposicion.estado == "Pendiente",
            )
            .scalar() or 0
        )

        criticos_count = (
            db.query(Producto)
            .outerjoin(Inventario, Producto.idProducto == Inventario.idProducto)
            .filter(
                Producto.estado == "ACTIVO",
                func.coalesce(Inventario.cantidadDisponible, 0) <= STOCK_CRITICO,
            )
            .count()
        )

        urgentes_count = (
            db.query(Producto)
            .outerjoin(Inventario, Producto.idProducto == Inventario.idProducto)
            .filter(
                Producto.estado == "ACTIVO",
                func.coalesce(Inventario.cantidadDisponible, 0) <= STOCK_BAJO,
            )
            .count()
        )

        estables_count = (
            db.query(Producto)
            .outerjoin(Inventario, Producto.idProducto == Inventario.idProducto)
            .filter(
                Producto.estado == "ACTIVO",
                func.coalesce(Inventario.cantidadDisponible, 0) > STOCK_BAJO,
            )
            .count()
        )

        health_score, health_status, health_subtitle = InventarioService._calcular_health_inventario(
            productos_activos, criticos_count
        )

        return {
            "kpis": {
                "productos_activos":     productos_activos,
                "stock_total":           stock_total,
                "riesgo_alto_critico":   criticos_count,
                "solicitudes_en_proceso": solicitudes_en_proceso,
                "reabastecimiento_urgente": urgentes_count,
                "inventario_estable":    estables_count,
                "salud_score":           health_score,
                "salud_status":          health_status,
                "salud_subtitle":        health_subtitle,
            }
        }

    @staticmethod
    def _calcular_health_inventario(
        productos_activos: int, criticos_count: int
    ) -> tuple[int, str, str]:
        """
        Calcula el health score del inventario (0–100) y su etiqueta textual.
        Retorna (score, status, subtitle).
        """
        score = (
            max(0, round(((productos_activos - criticos_count) / productos_activos) * 100))
            if productos_activos > 0
            else 100
        )

        if score >= 90:
            status   = "Excelente"
            subtitle = f"Significa que el {score}% de tu catálogo fluye sin riesgo de quiebre."
        elif score >= 70:
            status   = "Estable"
            subtitle = (
                f"El inventario está controlado, pero hay un {100 - score}% "
                "de artículos que requieren vigilancia."
            )
        elif score >= 50:
            status   = "Requiere Atención"
            subtitle = (
                f"Advertencia: El {100 - score}% de tu catálogo podría "
                "agotarse si no realizas reposiciones."
            )
        else:
            status   = "Crítico"
            subtitle = (
                f"¡Peligro! El {100 - score}% de tus productos están "
                "agotándose y perdiendo ventas potenciales."
            )

        return score, status, subtitle

    # ── Datos paginados del catálogo ─────────────────────────────────────────

    @staticmethod
    def get_inventario_data(
        db: Session,
        q: Optional[str],
        id_categoria: Optional[int],
        estado_stock: Optional[str],
        page: int,
        size: int,
    ) -> dict:
        """
        Retorna la página de productos enriquecida con métricas de inventario,
        riesgo, clasificación ABC y contexto semántico.
        """
        # 1. Construir query base con filtros
        query = (
            db.query(Producto)
            .outerjoin(Inventario, Producto.idProducto == Inventario.idProducto)
            .filter(Producto.estado == "ACTIVO")
        )

        if q:
            search_term = f"%{q}%"
            id_filter = [Producto.idProducto == int(q)] if q.isdigit() else []
            query = query.filter(
                or_(
                    Producto.codigoBarras == q,
                    Producto.codigoBarras.ilike(search_term),
                    Producto.nombre.ilike(search_term),
                    Producto.marca.ilike(search_term),
                    *id_filter,
                )
            )

        if id_categoria:
            query = query.filter(Producto.idCategoria == id_categoria)

        if estado_stock and estado_stock != "Todos":
            if estado_stock == "Crítico":
                query = query.filter(func.coalesce(Inventario.cantidadDisponible, 0) <= STOCK_CRITICO)
            elif estado_stock == "Bajo":
                query = query.filter(func.coalesce(Inventario.cantidadDisponible, 0).between(STOCK_CRITICO + 1, STOCK_BAJO))
            elif estado_stock == "Óptimo":
                query = query.filter(func.coalesce(Inventario.cantidadDisponible, 0) > STOCK_BAJO)

        # 2. Paginación
        total_records = query.count()
        pages         = math.ceil(total_records / size) if total_records > 0 else 1
        productos     = query.offset((page - 1) * size).limit(size).all()

        if not productos:
            return {
                "items": [], "productos": [],
                "total_records": total_records, "pages": pages,
                "current_page": page, "page_size": size,
            }

        # 3. Fix N+1: una sola query de ingresos para todos los productos de la página
        ids_pagina = [p.idProducto for p in productos]
        ingresos_por_producto = InventarioService._get_ingresos_batch(db, ids_pagina)

        # 4. Clasificación ABC (Pareto 80/20) sobre la página actual
        abc_classification = InventarioService._calcular_abc(productos, ingresos_por_producto)

        # 5. Solicitudes pendientes (una query, no N+1)
        solicitudes_pendientes = (
            db.query(SolicitudReposicion.idProducto, SolicitudReposicion.idSolicitud)
            .filter(SolicitudReposicion.estado == "Pendiente")
            .all()
        )
        map_solicitudes = {s[0]: s[1] for s in solicitudes_pendientes}

        # 6. Reglas Apriori en memoria (sin DB)
        reglas_activas = MineriaService._reglas

        # 7. Enriquecer cada producto
        resultados = []
        for prod in productos:
            stock_disp = prod.inventario.cantidadDisponible if prod.inventario else 0
            velocidad  = PrediccionService.calcular_velocidad_venta(db, prod.idProducto, 30)
            riesgo     = PrediccionService.clasificar_riesgo_quiebre(stock_disp, velocidad, 7)

            estado_fisico  = InventarioService.clasificar_estado_fisico(stock_disp)
            dias_quiebre   = InventarioService.calcular_dias_quiebre(stock_disp, velocidad)
            accion         = InventarioService.determinar_accion(dias_quiebre, velocidad)
            num_reglas     = InventarioService.contar_reglas_asociacion(prod.idProducto, reglas_activas)
            contexto       = InventarioService.generar_contexto(estado_fisico, velocidad, num_reglas, stock_disp)

            reglas_texto = (
                f"Suele comprarse junto con otros {num_reglas} productos"
                if num_reglas > 0
                else "No suele comprarse junto con otros artículos"
            )

            resultados.append({
                "idProducto":              prod.idProducto,
                "idCategoria":             prod.idCategoria,
                "codigoBarras":            prod.codigoBarras or "-",
                "nombre":                  prod.nombre,
                "categoria":               prod.categoria.nombreCategoria if prod.categoria else "-",
                "costo":                   float(prod.costoProducto),
                "precio":                  float(prod.precioLista),
                "talla":                   prod.talla or "",
                "color":                   prod.color or "",
                "marca":                   prod.marca or "",
                "margen":                  round(float(prod.margen_rentabilidad), 1),
                "stock":                   stock_disp,
                "velocidad":               round(velocidad, 2),
                "estado_fisico":           estado_fisico,
                "riesgo":                  riesgo,
                "abc":                     abc_classification.get(prod.idProducto, "C"),
                "dias_quiebre":            round(dias_quiebre, 1) if dias_quiebre != 9999 else None,
                "accion":                  accion,
                "reglas_vinculadas":       num_reglas,
                "reglas_vinculadas_texto": reglas_texto,
                "contexto_producto":       contexto,
                "ingresos_generados":      ingresos_por_producto.get(prod.idProducto, 0.0),
                "tiene_solicitud_pendiente": prod.idProducto in map_solicitudes,
                "id_solicitud_pendiente":  map_solicitudes.get(prod.idProducto),
            })

        resultados.sort(key=InventarioService.heuristica_orden, reverse=True)

        return {
            "items":         resultados,
            "productos":     resultados,
            "total_records": total_records,
            "pages":         pages,
            "current_page":  page,
            "page_size":     size,
        }

    # ── Helpers de enriquecimiento (puros / sin I/O) ─────────────────────────

    @staticmethod
    def clasificar_estado_fisico(stock: int) -> str:
        """Clasifica el nivel de stock usando los thresholds centralizados."""
        if stock <= STOCK_CRITICO:
            return "Crítico"
        if stock <= STOCK_BAJO:
            return "Bajo"
        return "Óptimo"

    @staticmethod
    def calcular_dias_quiebre(stock: int, velocidad: float) -> float:
        """Días estimados hasta que el stock llegue a cero. 9999 = sin riesgo."""
        return stock / velocidad if velocidad > 0 else 9999

    @staticmethod
    def determinar_accion(dias_quiebre: float, velocidad: float) -> str:
        """Recomendación de acción: Reponer / Liquidar / Mantener."""
        if dias_quiebre < 10:
            return "Reponer"
        if dias_quiebre > 90 and velocidad < 0.2:
            return "Liquidar"
        return "Mantener"

    @staticmethod
    def contar_reglas_asociacion(id_producto: int, reglas: dict) -> int:
        """Cuenta cuántas reglas Apriori involucran a este producto."""
        num = 0
        for antecedente, consecuentes in reglas.items():
            if id_producto == antecedente:
                num += len(consecuentes)
            else:
                num += sum(1 for c in consecuentes if c[0] == id_producto)
        return num

    @staticmethod
    def generar_contexto(
        estado_fisico: str,
        velocidad: float,
        num_reglas: int,
        stock: int,
    ) -> str:
        """Genera el texto de contexto semántico del producto para la UI."""
        if estado_fisico == "Crítico" and num_reglas > 0:
            return "✔ Impulsa la venta de otros productos"
        if estado_fisico == "Crítico":
            return "⚠️ Te quedarás sin stock pronto"
        if velocidad > 0.5:
            return "🔥 Se vende muy rápido"
        if velocidad == 0 and stock > 20:
            return "💤 No se está vendiendo"
        return "Stock sin problemas"

    @staticmethod
    def heuristica_orden(resultado: dict) -> tuple:
        """Clave de ordenamiento: críticos primero, luego por reglas vinculadas."""
        es_critico = 1 if resultado["estado_fisico"] == "Crítico" else 0
        return (es_critico, resultado["reglas_vinculadas"])

    # ── Fix N+1: ingresos en batch ────────────────────────────────────────────

    @staticmethod
    def _get_ingresos_batch(db: Session, ids: list[int]) -> dict[int, float]:
        """
        Obtiene los ingresos acumulados de una lista de productos en
        UNA SOLA QUERY usando GROUP BY, eliminando el patrón N+1.
        """
        if not ids:
            return {}
        rows = (
            db.query(
                DetalleVenta.idProducto,
                func.sum(DetalleVenta.subtotal).label("total"),
            )
            .filter(DetalleVenta.idProducto.in_(ids))
            .group_by(DetalleVenta.idProducto)
            .all()
        )
        result = {id_: 0.0 for id_ in ids}
        for id_producto, total in rows:
            result[id_producto] = float(total) if total else 0.0
        return result

    # ── Clasificación ABC (Pareto 80/20) ─────────────────────────────────────

    @staticmethod
    def _calcular_abc(
        productos: list, ingresos_map: dict[int, float]
    ) -> dict[int, str]:
        """
        Clasifica productos según la regla Pareto:
        A → acumula hasta el 80% de ingresos
        B → acumula hasta el 95%
        C → el resto
        """
        ordenados   = sorted(productos, key=lambda p: ingresos_map.get(p.idProducto, 0), reverse=True)
        ingreso_total = sum(ingresos_map.values())
        clasificacion: dict[int, str] = {}
        acumulado = 0.0

        for prod in ordenados:
            ingreso = ingresos_map.get(prod.idProducto, 0)
            if ingreso_total > 0:
                acumulado += ingreso
                pct = acumulado / ingreso_total
                if pct <= 0.80:
                    clasificacion[prod.idProducto] = "A"
                elif pct <= 0.95:
                    clasificacion[prod.idProducto] = "B"
                else:
                    clasificacion[prod.idProducto] = "C"
            else:
                clasificacion[prod.idProducto] = "C"

        return clasificacion

    # ── CRUD Categoría ───────────────────────────────────────────────────────

    @staticmethod
    def crear_categoria(db: Session, data: CategoriaCreate) -> dict:
        nombre_clean = data.nombreCategoria.strip()
        if not nombre_clean:
            raise HTTPException(status_code=400, detail="El nombre de la categoría no puede estar vacío")

        existente = (
            db.query(Categoria)
            .filter(func.lower(Categoria.nombreCategoria) == func.lower(nombre_clean))
            .first()
        )
        if existente:
            return {"id": existente.idCategoria, "nombre": existente.nombreCategoria, "existente": True}

        nueva = Categoria(nombreCategoria=nombre_clean, estado="ACTIVO")
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        return {"id": nueva.idCategoria, "nombre": nueva.nombreCategoria, "existente": False}

    # ── CRUD Producto ────────────────────────────────────────────────────────

    @staticmethod
    def crear_producto(db: Session, data: ProductoCreate) -> dict:
        cat = db.query(Categoria).filter(Categoria.idCategoria == data.idCategoria).first()
        if not cat:
            raise HTTPException(status_code=400, detail="La categoría seleccionada no existe")

        cod_clean = None
        if data.codigoBarras and data.codigoBarras.strip():
            cod_clean = data.codigoBarras.strip()
            if db.query(Producto).filter(Producto.codigoBarras == cod_clean).first():
                raise HTTPException(
                    status_code=400,
                    detail=f"El código de producto/barras '{cod_clean}' ya está registrado",
                )

        nuevo = Producto(
            idCategoria   = data.idCategoria,
            codigoBarras  = cod_clean,
            nombre        = data.nombre.strip(),
            costoProducto = data.costoProducto,
            precioLista   = data.precioLista,
            talla         = data.talla.strip() if data.talla else None,
            color         = data.color.strip() if data.color else None,
            marca         = data.marca.strip() if data.marca else None,
            estado        = "ACTIVO",
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)

        inv = Inventario(
            idProducto        = nuevo.idProducto,
            cantidadDisponible = max(0, data.stockInicial or 0),
        )
        db.add(inv)
        db.commit()

        return {
            "status":     "success",
            "message":    f"Producto '{nuevo.nombre}' creado exitosamente.",
            "idProducto": nuevo.idProducto,
        }

    @staticmethod
    def actualizar_producto(db: Session, id_producto: int, data: ProductoUpdate) -> dict:
        prod = db.query(Producto).filter(Producto.idProducto == id_producto).first()
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        if not db.query(Categoria).filter(Categoria.idCategoria == data.idCategoria).first():
            raise HTTPException(status_code=400, detail="La categoría seleccionada no existe")

        cod_clean = None
        if data.codigoBarras and data.codigoBarras.strip():
            cod_clean = data.codigoBarras.strip()
            conflicto = (
                db.query(Producto)
                .filter(Producto.codigoBarras == cod_clean, Producto.idProducto != id_producto)
                .first()
            )
            if conflicto:
                raise HTTPException(
                    status_code=400,
                    detail=f"El código '{cod_clean}' ya está asignado a otro producto",
                )

        prod.nombre        = data.nombre.strip()
        prod.idCategoria   = data.idCategoria
        prod.costoProducto = data.costoProducto
        prod.precioLista   = data.precioLista
        prod.codigoBarras  = cod_clean
        prod.talla         = data.talla.strip() if data.talla else None
        prod.color         = data.color.strip() if data.color else None
        prod.marca         = data.marca.strip() if data.marca else None

        db.commit()
        db.refresh(prod)

        return {"status": "success", "message": f"Producto '{prod.nombre}' actualizado exitosamente."}
