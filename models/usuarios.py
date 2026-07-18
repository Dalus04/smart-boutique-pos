from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

class Usuario(Base):
    __tablename__ = "usuario"

    idUsuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nombreUsuario: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    contrasena: Mapped[str] = mapped_column(String(100), nullable=False)
    rol: Mapped[str] = mapped_column(String(50), nullable=False, default="CAJERO")
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVO")

    # Relaciones bidireccionales (sin cascadas de eliminación para preservar historial)
    compras: Mapped[list["Compra"]] = relationship("Compra", back_populates="usuario")
    ventas: Mapped[list["Venta"]] = relationship("Venta", back_populates="usuario")
