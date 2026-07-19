from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional

from api.dependencies import get_db_session
from models.actores import Cliente, Proveedor

router = APIRouter(
    prefix="/api/v1/actores",
    tags=["Actores Comerciales"]
)

# Schemas Cliente
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

# Schemas Proveedor
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

# --- ENDPOINTS CLIENTES ---

@router.get("/clientes")
def get_clientes(db: Session = Depends(get_db_session)):
    clientes = db.query(Cliente).filter(Cliente.estado == 'ACTIVO').all()
    return [{
        "idCliente": c.idCliente,
        "tipoDocumento": c.tipoDocumento,
        "numeroDocumento": c.numeroDocumento,
        "nombres": c.nombres,
        "apellidos": c.apellidos,
        "telefono": c.telefono or "-",
        "correoElectronico": c.correoElectronico or "-"
    } for c in clientes]

@router.post("/clientes")
def create_cliente(payload: ClienteCreate, db: Session = Depends(get_db_session)):
    existente = db.query(Cliente).filter(Cliente.numeroDocumento == payload.numeroDocumento).first()
    if existente:
        raise HTTPException(status_code=400, detail="El número de documento ya está registrado.")
    
    nuevo_cliente = Cliente(**payload.model_dump())
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return {"status": "success", "idCliente": nuevo_cliente.idCliente}

@router.put("/clientes/{id}")
def update_cliente(id: int, payload: ClienteUpdate, db: Session = Depends(get_db_session)):
    cliente = db.query(Cliente).filter(Cliente.idCliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    existente = db.query(Cliente).filter(
        Cliente.numeroDocumento == payload.numeroDocumento, 
        Cliente.idCliente != id
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="El número de documento ya pertenece a otro cliente.")
        
    for var, value in payload.model_dump().items():
        setattr(cliente, var, value)
        
    db.commit()
    return {"status": "success"}

# --- ENDPOINTS PROVEEDORES ---

@router.get("/proveedores")
def get_proveedores(db: Session = Depends(get_db_session)):
    proveedores = db.query(Proveedor).filter(Proveedor.estado == 'ACTIVO').all()
    return [{
        "idProveedor": p.idProveedor,
        "tipoDocumento": p.tipoDocumento,
        "numeroDocumento": p.numeroDocumento,
        "nombreRazonSocial": p.nombreRazonSocial,
        "telefono": p.telefono or "-",
        "direccion": p.direccion or "-",
        "correoElectronico": p.correoElectronico or "-"
    } for p in proveedores]

@router.post("/proveedores")
def create_proveedor(payload: ProveedorCreate, db: Session = Depends(get_db_session)):
    existente = db.query(Proveedor).filter(Proveedor.numeroDocumento == payload.numeroDocumento).first()
    if existente:
        raise HTTPException(status_code=400, detail="El RUC ya está registrado.")
    
    nuevo_proveedor = Proveedor(**payload.model_dump())
    db.add(nuevo_proveedor)
    db.commit()
    db.refresh(nuevo_proveedor)
    return {"status": "success", "idProveedor": nuevo_proveedor.idProveedor}

@router.put("/proveedores/{id}")
def update_proveedor(id: int, payload: ProveedorUpdate, db: Session = Depends(get_db_session)):
    proveedor = db.query(Proveedor).filter(Proveedor.idProveedor == id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    existente = db.query(Proveedor).filter(
        Proveedor.numeroDocumento == payload.numeroDocumento, 
        Proveedor.idProveedor != id
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="El RUC ya pertenece a otro proveedor.")
        
    for var, value in payload.model_dump().items():
        setattr(proveedor, var, value)
        
    db.commit()
    return {"status": "success"}
