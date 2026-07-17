from decimal import Decimal
import datetime
from sqlalchemy import Integer, Numeric, Date, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

class Venta(Base):
    __tablename__ = "venta"

    idVenta: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idCliente: Mapped[int | None] = mapped_column(Integer, ForeignKey("cliente.idCliente"), nullable=True)
    idUsuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuario.idUsuario"), nullable=False)
    fechaVenta: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    montoTotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones bidireccionales (sin cascadas de eliminación para proteger el historial)
    cliente: Mapped["Cliente | None"] = relationship("Cliente", back_populates="ventas")
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="ventas")
    detalles: Mapped[list["DetalleVenta"]] = relationship("DetalleVenta", back_populates="venta")
    pagos: Mapped[list["Pago"]] = relationship("Pago", back_populates="venta")

    @property
    def total_articulos(self) -> int:
        """
        Calcula dinámicamente la suma de unidades de productos vendidas en esta transacción.
        """
        return sum(d.cantidad for d in self.detalles)

    def sugerencia_venta_cruzada(self) -> list[str]:
        """
        Esqueleto para lógica futura de sugerencia de venta cruzada (Recomendador).
        Por ejemplo, si compra zapatillas, sugerir medias o cordones deportivos.
        """
        # TODO: Implementar lógica de recomendación basada en los productos de los detalles.
        return []

class DetalleVenta(Base):
    __tablename__ = "detalle_venta"

    idDetalleVenta: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idVenta: Mapped[int] = mapped_column(Integer, ForeignKey("venta.idVenta"), nullable=False)
    idProducto: Mapped[int] = mapped_column(Integer, ForeignKey("producto.idProducto"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    costoUnitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    precioUnitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones bidireccionales (sin cascadas)
    venta: Mapped["Venta"] = relationship("Venta", back_populates="detalles")
    producto: Mapped["Producto"] = relationship("Producto", back_populates="detalles_venta")

class MedioPago(Base):
    __tablename__ = "medio_pago"

    idMedioPago: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombreMedioPago: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # Relación bidireccional uno-a-muchos (sin cascada)
    pagos: Mapped[list["Pago"]] = relationship("Pago", back_populates="medio_pago")

class Pago(Base):
    __tablename__ = "pago"

    idPago: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idVenta: Mapped[int] = mapped_column(Integer, ForeignKey("venta.idVenta"), nullable=False)
    idMedioPago: Mapped[int] = mapped_column(Integer, ForeignKey("medio_pago.idMedioPago"), nullable=False)
    fechaPago: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    montoPagado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones bidireccionales (sin cascadas)
    venta: Mapped["Venta"] = relationship("Venta", back_populates="pagos")
    medio_pago: Mapped["MedioPago"] = relationship("MedioPago", back_populates="pagos")
