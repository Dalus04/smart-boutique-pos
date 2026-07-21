from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from pydantic import BaseModel, Field

from api.dependencies import get_db_session
from models.catalogo import Producto, Categoria
from models.suministro import Inventario, SolicitudReposicion
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
                Producto.codigoBarras.ilike(search_term),
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

    # Obtener IDs de productos con solicitudes de reposición pendientes y su idSolicitud
    solicitudes_pendientes = db.query(SolicitudReposicion.idProducto, SolicitudReposicion.idSolicitud).filter(SolicitudReposicion.estado == 'Pendiente').all()
    map_solicitudes = {s[0]: s[1] for s in solicitudes_pendientes}
    
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
            "idCategoria": prod.idCategoria,
            "codigoBarras": prod.codigoBarras or "-",
            "nombre": prod.nombre,
            "categoria": prod.categoria.nombreCategoria if prod.categoria else "-",
            "costo": float(prod.costoProducto),
            "precio": float(prod.precioLista),
            "talla": prod.talla or "",
            "color": prod.color or "",
            "marca": prod.marca or "",
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
            "ingresos_generados": ingresos_por_producto.get(prod.idProducto, 0.0),
            "tiene_solicitud_pendiente": prod.idProducto in map_solicitudes,
            "id_solicitud_pendiente": map_solicitudes.get(prod.idProducto)
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

# Schemas y Endpoint para Crear/Editar Producto y Categoría

class CategoriaCreate(BaseModel):
    nombreCategoria: str

@router.post("/categoria")
def create_categoria(data: CategoriaCreate, db: Session = Depends(get_db_session)):
    nombre_clean = data.nombreCategoria.strip()
    if not nombre_clean:
        raise HTTPException(status_code=400, detail="El nombre de la categoría no puede estar vacío")

    existente = db.query(Categoria).filter(func.lower(Categoria.nombreCategoria) == func.lower(nombre_clean)).first()
    if existente:
        return {"id": existente.idCategoria, "nombre": existente.nombreCategoria, "existente": True}

    nueva_cat = Categoria(nombreCategoria=nombre_clean, estado="ACTIVO")
    db.add(nueva_cat)
    db.commit()
    db.refresh(nueva_cat)

    return {"id": nueva_cat.idCategoria, "nombre": nueva_cat.nombreCategoria, "existente": False}

class ProductoCreate(BaseModel):
    nombre: str
    idCategoria: int
    costoProducto: float
    precioLista: float
    codigoBarras: Optional[str] = None
    stockInicial: Optional[int] = 0
    talla: Optional[str] = None
    color: Optional[str] = None
    marca: Optional[str] = None

@router.post("/producto")
def create_producto(data: ProductoCreate, db: Session = Depends(get_db_session)):
    # Validar que la categoría exista
    cat = db.query(Categoria).filter(Categoria.idCategoria == data.idCategoria).first()
    if not cat:
        raise HTTPException(status_code=400, detail="La categoría seleccionada no existe")

    # Validar código de barras único si fue ingresado
    if data.codigoBarras and data.codigoBarras.strip():
        cod_clean = data.codigoBarras.strip()
        existente = db.query(Producto).filter(Producto.codigoBarras == cod_clean).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"El código de producto/barras '{cod_clean}' ya está registrado")
    else:
        cod_clean = None

    nuevo_prod = Producto(
        idCategoria=data.idCategoria,
        codigoBarras=cod_clean,
        nombre=data.nombre.strip(),
        costoProducto=data.costoProducto,
        precioLista=data.precioLista,
        talla=data.talla.strip() if data.talla else None,
        color=data.color.strip() if data.color else None,
        marca=data.marca.strip() if data.marca else None,
        estado="ACTIVO"
    )
    db.add(nuevo_prod)
    db.commit()
    db.refresh(nuevo_prod)

    # Crear el registro inicial en Inventario con 0 stock (se abastece en Compras)
    inv = Inventario(
        idProducto=nuevo_prod.idProducto,
        cantidadDisponible=max(0, data.stockInicial or 0)
    )
    db.add(inv)
    db.commit()

    return {
        "status": "success",
        "message": f"Producto '{nuevo_prod.nombre}' creado exitosamente.",
        "idProducto": nuevo_prod.idProducto
    }

class ProductoUpdate(BaseModel):
    nombre: str
    idCategoria: int
    costoProducto: float
    precioLista: float
    codigoBarras: Optional[str] = None
    talla: Optional[str] = None
    color: Optional[str] = None
    marca: Optional[str] = None

@router.put("/producto/{id_producto}")
def update_producto(id_producto: int, data: ProductoUpdate, db: Session = Depends(get_db_session)):
    prod = db.query(Producto).filter(Producto.idProducto == id_producto).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    cat = db.query(Categoria).filter(Categoria.idCategoria == data.idCategoria).first()
    if not cat:
        raise HTTPException(status_code=400, detail="La categoría seleccionada no existe")

    if data.codigoBarras and data.codigoBarras.strip():
        cod_clean = data.codigoBarras.strip()
        existente = db.query(Producto).filter(Producto.codigoBarras == cod_clean, Producto.idProducto != id_producto).first()
        if existente:
            raise HTTPException(status_code=400, detail=f"El código '{cod_clean}' ya está asignado a otro producto")
    else:
        cod_clean = None

    prod.nombre = data.nombre.strip()
    prod.idCategoria = data.idCategoria
    prod.costoProducto = data.costoProducto
    prod.precioLista = data.precioLista
    prod.codigoBarras = cod_clean
    prod.talla = data.talla.strip() if data.talla else None
    prod.color = data.color.strip() if data.color else None
    prod.marca = data.marca.strip() if data.marca else None

    db.commit()
    db.refresh(prod)

    return {
        "status": "success",
        "message": f"Producto '{prod.nombre}' actualizado exitosamente."
    }
