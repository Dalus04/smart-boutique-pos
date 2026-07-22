"""
Schemas Pydantic para el módulo de Punto de Venta (POS).
"""
from typing import List, Optional
from pydantic import BaseModel


class CartItem(BaseModel):
    idProducto: int
    cantidad: int
    precioUnitario: float
    costoUnitario: float


class CheckoutPayload(BaseModel):
    items: List[CartItem]
    idMedioPago: int
    montoTotal: float
    idCliente: Optional[int] = None  # Opcional (Ventas Rápidas)


class ContextoPayload(BaseModel):
    carrito_ids: List[int] = []
    idCliente: Optional[int] = None


class QuickClientePayload(BaseModel):
    numeroDocumento: str
    nombres: str
    apellidos: str
