"""
Router de Inventario.

Responsabilidad única: recibir requests HTTP, delegar al
InventarioService y devolver la response. Sin lógica de negocio.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db_session
from api.schemas.inventario import CategoriaCreate, ProductoCreate, ProductoUpdate
from models.catalogo import Producto, Categoria
from services.inventario import InventarioService
from services.prediccion import PrediccionService

router = APIRouter(
    prefix="/api/v1/inventario",
    tags=["Inventario"],
)


@router.get("/categorias")
def get_categorias(db: Session = Depends(get_db_session)):
    categorias = db.query(Categoria).filter(Categoria.estado == "ACTIVO").all()
    return [{"id": c.idCategoria, "nombre": c.nombreCategoria} for c in categorias]


@router.get("/kpis-globales")
def get_kpis_globales(db: Session = Depends(get_db_session)):
    """KPIs de alta velocidad para el tablero de inventario."""
    return InventarioService.get_kpis_globales(db)


@router.get("/data")
def get_inventario_data(
    q: Optional[str]           = Query(None, description="Búsqueda por ID, código, nombre o marca"),
    id_categoria: Optional[int] = Query(None, description="Filtro por ID de categoría"),
    estado_stock: Optional[str] = Query(None, description="Filtro por estado de stock"),
    page: int                   = Query(1, ge=1, description="Número de página"),
    size: int                   = Query(10, ge=1, le=100, description="Tamaño de página"),
    db: Session                 = Depends(get_db_session),
):
    return InventarioService.get_inventario_data(
        db=db,
        q=q,
        id_categoria=id_categoria,
        estado_stock=estado_stock,
        page=page,
        size=size,
    )


@router.post("/categoria")
def create_categoria(data: CategoriaCreate, db: Session = Depends(get_db_session)):
    return InventarioService.crear_categoria(db, data)


@router.post("/producto")
def create_producto(data: ProductoCreate, db: Session = Depends(get_db_session)):
    return InventarioService.crear_producto(db, data)


@router.put("/producto/{id_producto}")
def update_producto(
    id_producto: int,
    data: ProductoUpdate,
    db: Session = Depends(get_db_session),
):
    return InventarioService.actualizar_producto(db, id_producto, data)


@router.get("/pronostico/{id_producto}")
def get_pronostico(
    id_producto: int,
    meses: Optional[int] = Query(3, ge=1, le=12, description="Meses a proyectar"),
    db: Session           = Depends(get_db_session),
):
    """Pronóstico de demanda para un producto usando el PrediccionService."""
    if not db.query(Producto).filter(Producto.idProducto == id_producto).first():
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return PrediccionService.generar_pronostico_demanda(id_producto, meses, db)
