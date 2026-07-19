from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from api.dependencies import get_db_session
from models.catalogo import Producto, Categoria
from models.suministro import Inventario
from services.prediccion import PrediccionService

router = APIRouter(
    prefix="/api/v1/inventario",
    tags=["Inventario"]
)

@router.get("/categorias")
def get_categorias(db: Session = Depends(get_db_session)):
    categorias = db.query(Categoria).filter(Categoria.estado == 'ACTIVO').all()
    return [{"id": c.idCategoria, "nombre": c.nombreCategoria} for c in categorias]

@router.get("/data")
def get_inventario_data(
    q: Optional[str] = Query(None, description="Búsqueda por ID, código, nombre o marca"),
    id_categoria: Optional[int] = Query(None, description="Filtro por ID de categoría"),
    estado_stock: Optional[str] = Query(None, description="Filtro por estado de stock"),
    db: Session = Depends(get_db_session)
):
    query = db.query(Producto).filter(Producto.estado == 'ACTIVO')
    
    if q:
        # Búsqueda polimórfica
        search_term = f"%{q}%"
        # Si q es un número, intentar buscar por idProducto exacto
        id_filter = []
        if q.isdigit():
            id_filter.append(Producto.idProducto == int(q))
            
        query = query.filter(
            or_(
                Producto.codigoBarras == q,
                Producto.nombre.ilike(search_term),
                Producto.marca.ilike(search_term),
                *id_filter
            )
        )
        
    if id_categoria:
        query = query.filter(Producto.idCategoria == id_categoria)
        
    productos = query.all()
    
    resultados = []
    totales = {
        "productos_activos": len(productos),
        "stock_total": 0,
        "riesgo_alto_critico": 0,
        "categorias_activas": len(set(p.idCategoria for p in productos))
    }
    
    for prod in productos:
        # Stock
        stock_disp = prod.inventario.cantidadDisponible if prod.inventario else 0
        totales["stock_total"] += stock_disp
        
        # IA: Predicción y Estado
        velocidad = PrediccionService.calcular_velocidad_venta(db, prod.idProducto, 30)
        riesgo = PrediccionService.clasificar_riesgo_quiebre(stock_disp, velocidad, 7)
        
        estado_fisico = "Óptimo"
        if stock_disp <= 5:
            estado_fisico = "Crítico"
        elif stock_disp <= 15:
            estado_fisico = "Bajo"
            
        if estado_fisico == "Crítico" or riesgo == "Riesgo Alto":
            totales["riesgo_alto_critico"] += 1
            
        # Filtrado post-procesado (ya que depende del estado calculado)
        if estado_stock and estado_stock != "Todos" and estado_fisico != estado_stock:
            continue
            
        resultados.append({
            "idProducto": prod.idProducto,
            "codigoBarras": prod.codigoBarras or "-",
            "nombre": prod.nombre,
            "categoria": prod.categoria.nombreCategoria if prod.categoria else "-",
            "costo": float(prod.costoProducto),
            "precio": float(prod.precioLista),
            "margen": prod.margen_rentabilidad,
            "stock": stock_disp,
            "velocidad": round(velocidad, 2),
            "estado_fisico": estado_fisico,
            "riesgo": riesgo
        })
        
    return {
        "kpis": totales,
        "productos": resultados
    }
