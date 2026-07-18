from decimal import Decimal
from sqlalchemy import ForeignKey, Integer, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

class Categoria(Base):
    __tablename__ = "categoria"

    idCategoria: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombreCategoria: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    estado: Mapped[str | None] = mapped_column(String(20), nullable=True, default="ACTIVO")

    # Relación bidireccional uno-a-muchos (sin cascada para mantener la integridad histórica)
    productos: Mapped[list["Producto"]] = relationship(
        "Producto",
        back_populates="categoria"
    )

class Producto(Base):
    __tablename__ = "producto"

    idProducto: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idCategoria: Mapped[int] = mapped_column(Integer, ForeignKey("categoria.idCategoria"), nullable=False)
    codigoBarras: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    talla: Mapped[str | None] = mapped_column(String(20), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(50), nullable=True)
    material: Mapped[str | None] = mapped_column(String(50), nullable=True)
    costoProducto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    precioLista: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[str | None] = mapped_column(String(20), nullable=True, default="ACTIVO")

    # Relación bidireccional muchos-a-uno
    categoria: Mapped["Categoria"] = relationship("Categoria", back_populates="productos")

    # Relación bidireccional uno-a-uno con Inventario
    inventario: Mapped["Inventario | None"] = relationship("Inventario", back_populates="producto", uselist=False)
    
    # Relación bidireccional uno-a-muchos (sin cascada)
    detalles_compra: Mapped[list["DetalleCompra"]] = relationship("DetalleCompra", back_populates="producto")
    detalles_venta: Mapped[list["DetalleVenta"]] = relationship("DetalleVenta", back_populates="producto")

    @property
    def margen_rentabilidad(self) -> float:
        """
        Calcula el margen de rentabilidad bruta en porcentaje:
        ((precioLista - costoProducto) / precioLista) * 100
        Retorna 0.0 si el precioLista es 0 para evitar división por cero.
        """
        if not self.precioLista or self.precioLista == Decimal("0"):
            return 0.0
        
        costo = float(self.costoProducto)
        precio = float(self.precioLista)
        return ((precio - costo) / precio) * 100
