"""
Schemas Pydantic para el módulo de Inventario.

Separados del router para que puedan ser importados y reutilizados
en tests, otros routers o documentación sin arrastrar lógica HTTP.
"""
from typing import Optional
from pydantic import BaseModel


class CategoriaCreate(BaseModel):
    nombreCategoria: str


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


class ProductoUpdate(BaseModel):
    nombre: str
    idCategoria: int
    costoProducto: float
    precioLista: float
    codigoBarras: Optional[str] = None
    talla: Optional[str] = None
    color: Optional[str] = None
    marca: Optional[str] = None
