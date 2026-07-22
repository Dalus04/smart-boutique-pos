from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from api.dependencies import get_db_session
from services.analitica import AnaliticaService
from services.mineria import MineriaService
from models.catalogo import Producto
from models.suministro import Compra
from models.pos import Venta
import datetime

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"]
)

@router.get("/metrics")
def get_dashboard_metrics(
    periodo: str = Query("7_dias", description="Periodo de consulta (hoy, 7_dias, mes, anio, todo, custom)"),
    fecha_inicio: datetime.date = Query(None, description="Fecha de inicio para filtro personalizado (YYYY-MM-DD)"),
    fecha_fin: datetime.date = Query(None, description="Fecha de fin para filtro personalizado (YYYY-MM-DD)"),
    db: Session = Depends(get_db_session)
):
    periodo_val = periodo if isinstance(periodo, str) else "7_dias"
    f_inicio = fecha_inicio if isinstance(fecha_inicio, datetime.date) else None
    f_fin = fecha_fin if isinstance(fecha_fin, datetime.date) else None

    try:
        # Métricas base + health score + regresión (todo calculado en servidor)
        metricas = AnaliticaService.obtener_metricas_completas(
            db,
            periodo=periodo_val,
            fecha_inicio_custom=f_inicio,
            fecha_fin_custom=f_fin
        )

        # Reglas de asociación Apriori
        reglas = MineriaService.obtener_mejores_reglas(limit=3)

        reglas_nom = []
        for a_id, c_id, conf, sop, lift in reglas:
            a_nom = db.query(Producto.nombre).filter(Producto.idProducto == a_id).scalar()
            c_nom = db.query(Producto.nombre).filter(Producto.idProducto == c_id).scalar()
            reglas_nom.append((a_nom, c_nom, conf, sop, lift))

        metricas["reglas"] = reglas_nom

        # Insights dinámicos de minería
        insights = MineriaService.obtener_insights(metricas)
        metricas["insights"] = insights

        # ── Centro de Operaciones ─────────────────────────────────────────────
        # 1. Compras Pendientes (Borrador o Emitida)
        compras_pendientes = db.query(func.count(Compra.idCompra)).filter(
            Compra.estado.in_(["Borrador", "Emitida"])
        ).scalar() or 0
        metricas["compras_pendientes"] = compras_pendientes

        # Enriquecer el contexto de health con las compras pendientes
        metricas["health"]["contexto"].append({
            "warn":  compras_pendientes > 0,
            "label": f"{compras_pendientes} orden(es) de compra pendientes"
                     if compras_pendientes > 0
                     else "Sin órdenes de compra pendientes"
        })

        # 2. Clientes nuevos en el mes (primer ticket registrado este mes)
        now        = datetime.datetime.now()
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        subq = (
            db.query(Venta.idCliente, func.min(Venta.fechaVenta).label("primera_venta"))
            .group_by(Venta.idCliente)
            .subquery()
        )
        clientes_nuevos_mes = db.query(func.count(subq.c.idCliente)).filter(
            subq.c.primera_venta >= inicio_mes,
            subq.c.primera_venta <= now
        ).scalar() or 0
        metricas["clientes_nuevos_mes"] = clientes_nuevos_mes

        return metricas

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
