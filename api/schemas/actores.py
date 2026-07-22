"""
Schemas Pydantic para el módulo de Actores Comerciales (Clientes y Proveedores).
"""
from typing import Optional
from pydantic import BaseModel, Field


# ── Schemas Cliente ─────────────────────────────────────────────────────────

class ClienteBase(BaseModel):
    tipoDocumento: str = Field(..., description="DNI o RUC")
    numeroDocumento: str = Field(..., description="Exactamente 8 u 11 dígitos")
    nombres: str
    apellidos: str
    telefono: Optional[str] = None
    correoElectronico: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    pass


# ── Schemas Proveedor ───────────────────────────────────────────────────────

class ProveedorBase(BaseModel):
    tipoDocumento: str = Field(default="RUC")
    numeroDocumento: str = Field(..., description="Exactamente 11 dígitos")
    nombreRazonSocial: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    correoElectronico: Optional[str] = None


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorUpdate(ProveedorBase):
    pass
