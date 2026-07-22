"""
Schemas Pydantic para el módulo de Suministro y Compras.
"""
from typing import List, Optional
from pydantic import BaseModel


class SolicitudReposicionCreate(BaseModel):
    idProducto: int
    cantidad_sugerida: int
    motivo: str
    origen: Optional[str] = "Manual"  # IA, Manual


class CompraItem(BaseModel):
    idProducto: int
    cantidad: int
    costoUnitario: float


class RegistrarCompraPayload(BaseModel):
    idProveedor: int
    items: List[CompraItem]
    montoTotal: float
    estado: str = "Borrador"


class EstadoCompraPayload(BaseModel):
    estado: str


class SyncBorradorItem(BaseModel):
    idProducto: int
    cantidad: int
    costoUnitario: float


class SyncBorradorPayload(BaseModel):
    idProveedor: int
    items: List[SyncBorradorItem]
    montoTotal: float
