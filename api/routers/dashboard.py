from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from api.dependencies import get_db_session
from services.analitica import AnaliticaService
from services.mineria import MineriaService
from models.catalogo import Producto

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"]
)

@router.get("/metrics")
def get_dashboard_metrics(
    periodo: str = Query("7_dias", description="Periodo de consulta (hoy, 7_dias, mes, anio)"),
    db: Session = Depends(get_db_session)
):
    try:
        # Obtener métricas base
        metricas = AnaliticaService.obtener_metricas_completas(db, periodo)
        
        # Obtener reglas de asociación para los insights
        reglas = MineriaService.obtener_mejores_reglas(limit=3)
        
        # Resolver nombres de productos para reglas
        reglas_nom = []
        for a_id, c_id, conf, sop, lift in reglas:
            a_nom = db.query(Producto.nombre).filter(Producto.idProducto == a_id).scalar()
            c_nom = db.query(Producto.nombre).filter(Producto.idProducto == c_id).scalar()
            reglas_nom.append((a_nom, c_nom, conf, sop, lift))
            
        metricas["reglas"] = reglas_nom
        
        # Variación de proyección (aproximación lineal)
        if "proyeccion" not in metricas["kpis"]:
            metricas["kpis"]["proyeccion"] = {"var": metricas["kpis"].get("ventas", {}).get("var", 0)}
        
        # Obtener Insights Dinámicos
        insights = MineriaService.obtener_insights(metricas)
        metricas["insights"] = insights
        
        return metricas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
