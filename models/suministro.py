from decimal import Decimal
import datetime
from sqlalchemy import Integer, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

class Inventario(Base):
    __tablename__ = "inventario"

    idInventario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idProducto: Mapped[int] = mapped_column(Integer, ForeignKey("producto.idProducto"), nullable=False)
    fechaActualizacion: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    cantidadDisponible: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relación bidireccional muchos-a-uno (sin cascada de eliminación)
    producto: Mapped["Producto"] = relationship("Producto", back_populates="inventarios")

    @property
    def estado_stock(self) -> str:
        """
        Clasifica el nivel de stock actual:
        - <= 5: 'Crítico'
        - <= 15: 'Bajo'
        - > 15: 'Óptimo'
        """
        if self.cantidadDisponible <= 5:
            return "Crítico"
        elif self.cantidadDisponible <= 15:
            return "Bajo"
        return "Óptimo"

class Compra(Base):
    __tablename__ = "compra"

    idCompra: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idProveedor: Mapped[int] = mapped_column(Integer, ForeignKey("proveedor.idProveedor"), nullable=False)
    idUsuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuario.idUsuario"), nullable=False)
    fechaCompra: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    montoTotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones bidireccionales (sin cascada de eliminación)
    proveedor: Mapped["Proveedor"] = relationship("Proveedor", back_populates="compras")
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="compras")
    detalles: Mapped[list["DetalleCompra"]] = relationship("DetalleCompra", back_populates="compra")

class DetalleCompra(Base):
    __tablename__ = "detalle_compra"

    idDetalleCompra: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idCompra: Mapped[int] = mapped_column(Integer, ForeignKey("compra.idCompra"), nullable=False)
    idProducto: Mapped[int] = mapped_column(Integer, ForeignKey("producto.idProducto"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    costoUnitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones bidireccionales (sin cascada de eliminación)
    compra: Mapped["Compra"] = relationship("Compra", back_populates="detalles")
    producto: Mapped["Producto"] = relationship("Producto", back_populates="detalles_compra")
