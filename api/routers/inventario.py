import math
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

@router.get("/kpis-globales")
def get_kpis_globales(db: Session = Depends(get_db_session)):
    """
    Endpoint ligero de alta velocidad (<15ms) para calcular agregados globales SQL
    de las tarjetas del tablero de inventario.
    """
    productos_activos = db.query(Producto).filter(Producto.estado == 'ACTIVO').count()

    stock_total_res = db.query(func.coalesce(func.sum(Inventario.cantidadDisponible), 0))\
        .join(Producto, Inventario.idProducto == Producto.idProducto)\
        .filter(Producto.estado == 'ACTIVO').scalar()
    stock_total = int(stock_total_res or 0)

    solicitudes_en_proceso = db.query(func.count(func.distinct(SolicitudReposicion.idProducto)))\
        .join(Producto, SolicitudReposicion.idProducto == Producto.idProducto)\
        .filter(Producto.estado == 'ACTIVO', SolicitudReposicion.estado == 'Pendiente').scalar() or 0

    criticos_count = db.query(Producto).outerjoin(Inventario, Producto.idProducto == Inventario.idProducto)\
        .filter(Producto.estado == 'ACTIVO', func.coalesce(Inventario.cantidadDisponible, 0) <= 5).count()

    urgentes_count = db.query(Producto).outerjoin(Inventario, Producto.idProducto == Inventario.idProducto)\
        .filter(Producto.estado == 'ACTIVO', func.coalesce(Inventario.cantidadDisponible, 0) <= 15).count()

    estables_count = db.query(Producto).outerjoin(Inventario, Producto.idProducto == Inventario.idProducto)\
        .filter(Producto.estado == 'ACTIVO', func.coalesce(Inventario.cantidadDisponible, 0) > 15).count()

    health_score = max(0, round(((productos_activos - criticos_count) / productos_activos) * 100)) if productos_activos > 0 else 100

    if health_score >= 90:
        health_status = "Excelente"
        health_subtitle = f"Significa que el {health_score}% de tu catálogo fluye sin riesgo de quiebre."
    elif health_score >= 70:
        health_status = "Estable"
        health_subtitle = f"El inventario está controlado, pero hay un {100 - health_score}% de artículos que requieren vigilancia."
    elif health_score >= 50:
        health_status = "Requiere Atención"
        health_subtitle = f"Advertencia: El {100 - health_score}% de tu catálogo podría agotarse si no realizas reposiciones."
    else:
        health_status = "Crítico"
        health_subtitle = f"¡Peligro! El {100 - health_score}% de tus productos están agotándose y perdiendo ventas potenciales."

    return {
        "kpis": {
            "productos_activos": productos_activos,
            "stock_total": stock_total,
            "riesgo_alto_critico": criticos_count,
            "solicitudes_en_proceso": solicitudes_en_proceso,
            "reabastecimiento_urgente": urgentes_count,
            "inventario_estable": estables_count,
            "salud_score": health_score,
            "salud_status": health_status,
            "salud_subtitle": health_subtitle
        }
    }

@router.get("/data")
def get_inventario_data(
    q: Optional[str] = Query(None, description="Búsqueda por ID, código, nombre o marca"),
    id_categoria: Optional[int] = Query(None, description="Filtro por ID de categoría"),
    estado_stock: Optional[str] = Query(None, description="Filtro por estado de stock"),
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db_session)
):
    query = db.query(Producto).outerjoin(Inventario, Producto.idProducto == Inventario.idProducto).filter(Producto.estado == 'ACTIVO')
    
    if q:
        search_term = f"%{q}%"
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
        
    if estado_stock and estado_stock != "Todos":
        if estado_stock == "Crítico":
            query = query.filter(func.coalesce(Inventario.cantidadDisponible, 0) <= 5)
        elif estado_stock == "Bajo":
            query = query.filter(func.coalesce(Inventario.cantidadDisponible, 0).between(6, 15))
        elif estado_stock == "Óptimo":
            query = query.filter(func.coalesce(Inventario.cantidadDisponible, 0) > 15)

    total_records = query.count()
    pages = math.ceil(total_records / size) if total_records > 0 else 1
    
    # Aplicar Paginación SQL nativa
    productos = query.offset((page - 1) * size).limit(size).all()
    
    # Calcular ingresos acumulados para clasificación ABC (Pareto) sobre la página actual o general
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
            
    reglas_activas = MineriaService._reglas

    solicitudes_pendientes = db.query(SolicitudReposicion.idProducto, SolicitudReposicion.idSolicitud).filter(SolicitudReposicion.estado == 'Pendiente').all()
    map_solicitudes = {s[0]: s[1] for s in solicitudes_pendientes}
    
    resultados = []
    
    for prod in productos:
        stock_disp = prod.inventario.cantidadDisponible if prod.inventario else 0
        
        velocidad = PrediccionService.calcular_velocidad_venta(db, prod.idProducto, 30)
        riesgo = PrediccionService.clasificar_riesgo_quiebre(stock_disp, velocidad, 7)
        
        estado_fisico = "Óptimo"
        if stock_disp <= 5:
            estado_fisico = "Crítico"
        elif stock_disp <= 15:
            estado_fisico = "Bajo"
            
        dias_quiebre = stock_disp / velocidad if velocidad > 0 else 9999
        
        if dias_quiebre < 10:
            accion = "Reponer"
        elif dias_quiebre > 90 and velocidad < 0.2:
            accion = "Liquidar"
        else:
            accion = "Mantener"
            
        num_reglas = 0
        for antecedente, consecuentes in reglas_activas.items():
            if prod.idProducto == antecedente:
                num_reglas += len(consecuentes)
            else:
                num_reglas += sum(1 for c in consecuentes if c[0] == prod.idProducto)
            
        reglas_texto = f"Suele comprarse junto con otros {num_reglas} productos" if num_reglas > 0 else "No suele comprarse junto con otros artículos"

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
        
    def heuristica_orden(r):
        es_critico = 1 if r["estado_fisico"] == "Crítico" else 0
        return (es_critico, r["reglas_vinculadas"])
        
    resultados.sort(key=heuristica_orden, reverse=True)
        
    return {
        "items": resultados,
        "productos": resultados,
        "total_records": total_records,
        "pages": pages,
        "current_page": page,
        "page_size": size
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

@router.get("/pronostico/{id_producto}")
def get_pronostico(id_producto: int, meses: Optional[int] = Query(3, ge=1, le=12, description="Meses a proyectar"), db: Session = Depends(get_db_session)):
    """
    Genera un pronóstico de demanda para un producto en particular usando el PrediccionService.
    """
    # Validar que el producto exista
    prod = db.query(Producto).filter(Producto.idProducto == id_producto).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    resultado = PrediccionService.generar_pronostico_demanda(id_producto, meses, db)
    return resultado
