import random
from datetime import datetime, timedelta
from decimal import Decimal
import os
import sys

# Asegurar que los módulos del proyecto estén en el path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.db import engine, SessionLocal
from models.base import Base
from models.actores import Cliente, Proveedor
from models.catalogo import Categoria, Producto
from models.pos import Venta, DetalleVenta, MedioPago, Pago
from models.suministro import Inventario
from models.usuarios import Usuario

# 1. Recrear BD
print("Eliminando tablas antiguas...")
Base.metadata.drop_all(engine)
print("Creando estructura de base de datos...")
Base.metadata.create_all(engine)

def seed_db():
    db = SessionLocal()
    try:
        print("Poblando Usuarios...")
        u1 = Usuario(nombres="Admin", apellidos="System", nombreUsuario="admin", contrasena="admin", rol="ADMINISTRADOR")
        u2 = Usuario(nombres="Juan", apellidos="Cajero", nombreUsuario="cajero1", contrasena="1234", rol="CAJERO")
        db.add_all([u1, u2])
        
        print("Poblando Medios de Pago...")
        m1 = MedioPago(nombreMedioPago="Efectivo")
        m2 = MedioPago(nombreMedioPago="Tarjeta de Crédito")
        m3 = MedioPago(nombreMedioPago="Transferencia")
        db.add_all([m1, m2, m3])
        
        print("Poblando Clientes...")
        c1 = Cliente(numeroDocumento="12345678", nombres="Maria", apellidos="Lopez", telefono="987654321")
        c2 = Cliente(numeroDocumento="87654321", nombres="Carlos", apellidos="Perez", telefono="999888777")
        c3 = Cliente(numeroDocumento="11223344", nombres="Ana", apellidos="Gomez", telefono="911222333")
        db.add_all([c1, c2, c3])
        
        print("Poblando Categorías...")
        cat_camisas = Categoria(nombreCategoria="Camisas")
        cat_pantalones = Categoria(nombreCategoria="Pantalones")
        cat_accesorios = Categoria(nombreCategoria="Accesorios")
        db.add_all([cat_camisas, cat_pantalones, cat_accesorios])
        db.flush()

        print("Poblando Productos e Inventario...")
        # Prod 1: Alta rentabilidad, stock óptimo
        p1 = Producto(idCategoria=cat_camisas.idCategoria, codigoBarras="CAM-01", nombre="Camisa Oxford Blanca", precioLista=50.00, costoProducto=15.00)
        # Prod 2: Baja rentabilidad, stock bajo
        p2 = Producto(idCategoria=cat_pantalones.idCategoria, codigoBarras="PAN-01", nombre="Jean Clásico Azul", precioLista=40.00, costoProducto=35.00)
        # Prod 3: Alta rentabilidad, stock crítico
        p3 = Producto(idCategoria=cat_accesorios.idCategoria, codigoBarras="ACC-01", nombre="Corbata de Seda Negra", precioLista=25.00, costoProducto=5.00)
        # Prod 4: Normal
        p4 = Producto(idCategoria=cat_accesorios.idCategoria, codigoBarras="ACC-02", nombre="Cinturón de Cuero", precioLista=30.00, costoProducto=10.00)
        
        db.add_all([p1, p2, p3, p4])
        db.flush()

        # Inventario
        inv1 = Inventario(idProducto=p1.idProducto, cantidadDisponible=50) # Óptimo
        inv2 = Inventario(idProducto=p2.idProducto, cantidadDisponible=10) # Bajo
        inv3 = Inventario(idProducto=p3.idProducto, cantidadDisponible=3)  # Crítico
        inv4 = Inventario(idProducto=p4.idProducto, cantidadDisponible=20) # Óptimo
        db.add_all([inv1, inv2, inv3, inv4])
        
        print("Simulando Ventas Históricas (Apriori Training)...")
        # Generar ventas en los últimos 3 meses
        now = datetime.now()
        
        # Asociación Apriori: Camisa + Corbata (para que salga en Venta Cruzada)
        for i in range(15):
            dias_atras = random.randint(1, 90)
            fecha_venta = now - timedelta(days=dias_atras)
            
            venta = Venta(idCliente=c1.idCliente, idUsuario=u1.idUsuario, montoTotal=75.00, fechaVenta=fecha_venta)
            db.add(venta)
            db.flush()
            
            d1 = DetalleVenta(idVenta=venta.idVenta, idProducto=p1.idProducto, cantidad=1, costoUnitario=p1.costoProducto, precioUnitario=p1.precioLista, subtotal=p1.precioLista)
            d2 = DetalleVenta(idVenta=venta.idVenta, idProducto=p3.idProducto, cantidad=1, costoUnitario=p3.costoProducto, precioUnitario=p3.precioLista, subtotal=p3.precioLista)
            db.add_all([d1, d2])
            
            pago = Pago(idVenta=venta.idVenta, idMedioPago=m1.idMedioPago, montoPagado=75.00, fechaPago=fecha_venta)
            db.add(pago)

        # Asociación Apriori: Pantalón + Cinturón
        for i in range(10):
            dias_atras = random.randint(1, 90)
            fecha_venta = now - timedelta(days=dias_atras)
            
            venta = Venta(idCliente=c2.idCliente, idUsuario=u2.idUsuario, montoTotal=70.00, fechaVenta=fecha_venta)
            db.add(venta)
            db.flush()
            
            d1 = DetalleVenta(idVenta=venta.idVenta, idProducto=p2.idProducto, cantidad=1, costoUnitario=p2.costoProducto, precioUnitario=p2.precioLista, subtotal=p2.precioLista)
            d2 = DetalleVenta(idVenta=venta.idVenta, idProducto=p4.idProducto, cantidad=1, costoUnitario=p4.costoProducto, precioUnitario=p4.precioLista, subtotal=p4.precioLista)
            db.add_all([d1, d2])
            
            pago = Pago(idVenta=venta.idVenta, idMedioPago=m2.idMedioPago, montoPagado=70.00, fechaPago=fecha_venta)
            db.add(pago)

        # Ventas Random Recientes para el Dashboard (Hoy y Semana)
        for i in range(5):
            dias_atras = random.randint(0, 5) # Ventas recientes
            fecha_venta = now - timedelta(days=dias_atras)
            
            venta = Venta(idCliente=c3.idCliente, idUsuario=u2.idUsuario, montoTotal=50.00, fechaVenta=fecha_venta)
            db.add(venta)
            db.flush()
            
            d1 = DetalleVenta(idVenta=venta.idVenta, idProducto=p1.idProducto, cantidad=1, costoUnitario=p1.costoProducto, precioUnitario=p1.precioLista, subtotal=p1.precioLista)
            db.add(d1)
            
            pago = Pago(idVenta=venta.idVenta, idMedioPago=m3.idMedioPago, montoPagado=50.00, fechaPago=fecha_venta)
            db.add(pago)

        db.commit()
        print("¡Base de datos poblada exitosamente!")
    
    except Exception as e:
        db.rollback()
        print(f"Error poblando BD: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
