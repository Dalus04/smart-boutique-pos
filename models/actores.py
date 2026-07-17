from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

class Cliente(Base):
    __tablename__ = "cliente"

    idCliente: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nombresCompletos: Mapped[str] = mapped_column(String(150), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    correoElectronico: Mapped[str | None] = mapped_column(String(100), nullable=True)

class Proveedor(Base):
    __tablename__ = "proveedor"

    idProveedor: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    nombreRazonSocial: Mapped[str] = mapped_column(String(150), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    correoElectronico: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relación bidireccional uno-a-muchos (sin cascada)
    compras: Mapped[list["Compra"]] = relationship("Compra", back_populates="proveedor")
