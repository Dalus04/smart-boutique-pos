from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

class Administrador(Base):
    __tablename__ = "administrador"

    idAdministrador: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    contrasena: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relación bidireccional uno-a-muchos (sin cascada de eliminación)
    usuarios: Mapped[list["Usuario"]] = relationship("Usuario", back_populates="administrador")

class Usuario(Base):
    __tablename__ = "usuario"

    idUsuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    idAdministrador: Mapped[int | None] = mapped_column(Integer, ForeignKey("administrador.idAdministrador"), nullable=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nombreUsuario: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    contrasena: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relaciones bidireccionales (sin cascadas de eliminación para preservar historial)
    administrador: Mapped["Administrador | None"] = relationship("Administrador", back_populates="usuarios")
    compras: Mapped[list["Compra"]] = relationship("Compra", back_populates="usuario")
