from models.base import Base
from models.actores import Cliente, Proveedor
from models.catalogo import Categoria, Producto
from models.pos import Venta, DetalleVenta
from models.suministro import Inventario, Compra, DetalleCompra, SolicitudReposicion
from models.usuarios import Usuario

# Al importar este paquete, se registran todos los modelos en el registry de SQLAlchemy.
__all__ = [
    "Base",
    "Cliente", "Proveedor",
    "Categoria", "Producto",
    "Venta", "DetalleVenta",
    "Inventario", "Compra", "DetalleCompra", "SolicitudReposicion",
    "Usuario"
]
