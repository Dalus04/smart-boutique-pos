from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional

from api.dependencies import get_db_session
from models.catalogo import Producto, Categoria
from models.suministro import Inventario
from models.pos import DetalleVenta
from services.prediccion import PrediccionService
from services.mineria import MineriaService

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
    
    # Calcular ingresos acumulados para clasificación ABC (Pareto)
    ingresos_por_producto = {}
    for p in productos:
        ingresos = db.query(func.sum(DetalleVenta.subtotal)).filter(DetalleVenta.idProducto == p.idProducto).scalar()
        ingresos_por_producto[p.idProducto] = float(ingresos) if ingresos else 0.0

    productos_ordenados = sorted(productos, key=lambda p: ingresos_por_producto[p.idProducto], reverse=True)
    ingreso_total = sum(ingresos_por_producto.values())
    
    abc_classification = {}
    acumulado = 0.0
    for p in productos_ordenados:
        ingreso = ingresos_por_producto[p.idProducto]
        if ingreso_total > 0:
            acumulado += ingreso
            porcentaje = acumulado / ingreso_total
            if porcentaje <= 0.80:
                abc_classification[p.idProducto] = 'A'
            elif porcentaje <= 0.95:
                abc_classification[p.idProducto] = 'B'
            else:
                abc_classification[p.idProducto] = 'C'
        else:
            abc_classification[p.idProducto] = 'C'
            
    # Obtener reglas activas de Apriori en memoria
    reglas_activas = MineriaService._reglas
    
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
            
        # Filtrado post-procesado
        if estado_stock and estado_stock != "Todos" and estado_fisico != estado_stock:
            continue
            
        # Días Restantes para Quiebre
        dias_quiebre = stock_disp / velocidad if velocidad > 0 else 9999
        
        # Acción Comercial Sugerida
        if dias_quiebre < 10:
            accion = "Reponer"
        elif dias_quiebre > 90 and velocidad < 0.2:
            accion = "Liquidar"
        else:
            accion = "Mantener"
            
        # Conteo de Reglas Vinculadas
        num_reglas = 0
        for antecedente, consecuentes in reglas_activas.items():
            if prod.idProducto == antecedente:
                num_reglas += len(consecuentes)
            else:
                num_reglas += sum(1 for c in consecuentes if c[0] == prod.idProducto)
            
        reglas_texto = f"Suele comprarse junto con otros {num_reglas} productos" if num_reglas > 0 else "No suele comprarse junto con otros artículos"

        # Contexto del Producto (Subtítulo Contextual)
        if estado_fisico == "Crítico" and num_reglas > 0:
            contexto_producto = "✔ Impulsa la venta de otros productos"
        elif estado_fisico == "Crítico":
            contexto_producto = "⚠️ Te quedarás sin stock pronto"
        elif velocidad > 0.5:
            contexto_producto = "🔥 Se vende muy rápido"
        elif velocidad == 0 and stock_disp > 20:
            contexto_producto = "💤 No se está vendiendo"
        else:
            contexto_producto = "Stock sin problemas"
            
        resultados.append({
            "idProducto": prod.idProducto,
            "codigoBarras": prod.codigoBarras or "-",
            "nombre": prod.nombre,
            "categoria": prod.categoria.nombreCategoria if prod.categoria else "-",
            "costo": float(prod.costoProducto),
            "precio": float(prod.precioLista),
            "margen": round(float(prod.margen_rentabilidad), 1),
            "stock": stock_disp,
            "velocidad": round(velocidad, 2),
            "estado_fisico": estado_fisico,
            "riesgo": riesgo,
            "abc": abc_classification.get(prod.idProducto, 'C'),
            "dias_quiebre": round(dias_quiebre, 1) if dias_quiebre != 9999 else None,
            "accion": accion,
            "reglas_vinculadas": num_reglas,
            "reglas_vinculadas_texto": reglas_texto,
            "contexto_producto": contexto_producto,
            "ingresos_generados": ingresos_por_producto.get(prod.idProducto, 0.0)
        })
        
    # Ordenamiento Heurístico Eficiente: Críticos primero, luego por número de reglas descendente
    def heuristica_orden(r):
        es_critico = 1 if r["estado_fisico"] == "Crítico" else 0
        return (es_critico, r["reglas_vinculadas"])
        
    resultados.sort(key=heuristica_orden, reverse=True)
        
    return {
        "kpis": totales,
        "productos": resultados
    }
