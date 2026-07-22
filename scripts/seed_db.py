import random
from datetime import datetime, timedelta
from decimal import Decimal
import os
import sys

# Asegurar que los módulos del proyecto estén en el path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.db import engine, SessionLocal
from models.base import Base
from models.actores import Cliente, Proveedor
from models.catalogo import Categoria, Producto
from models.pos import Venta, DetalleVenta, MedioPago, Pago
from models.suministro import Inventario, Compra, DetalleCompra, SolicitudReposicion
from models.usuarios import Usuario

def seed_db():
    print("Eliminando tablas antiguas...")
    Base.metadata.drop_all(engine)
    print("Creando estructura de base de datos...")
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        print("Poblando Usuarios...")
        u1 = Usuario(nombres="Admin", apellidos="System", nombreUsuario="admin", contrasena="admin", rol="ADMINISTRADOR")
        u2 = Usuario(nombres="Juan", apellidos="Cajero", nombreUsuario="cajero1", contrasena="1234", rol="CAJERO")
        db.add_all([u1, u2])
        
        print("Poblando Medios de Pago...")
        m1 = MedioPago(nombreMedioPago="Efectivo")
        m2 = MedioPago(nombreMedioPago="Tarjeta de Crédito")
        m3 = MedioPago(nombreMedioPago="Transferencia (Yape/Plin)")
        db.add_all([m1, m2, m3])
        
        print("Poblando Proveedores...")
        prov1 = Proveedor(numeroDocumento="20512345678", nombreRazonSocial="Textiles Andinos S.A.C.", telefono="014523321", direccion="Av. Gamarra 450, Lima", correoElectronico="contacto@textilesandinos.pe")
        prov2 = Proveedor(numeroDocumento="20601122334", nombreRazonSocial="Confecciones Moda Global E.I.R.L.", telefono="013216549", direccion="Calle Los Mercaderes 120, Lima", correoElectronico="ventas@modaglobal.pe")
        prov3 = Proveedor(numeroDocumento="20549182931", nombreRazonSocial="Importadora El Elegante S.A.", telefono="019876543", direccion="Av. Primavera 890, Surco", correoElectronico="pedidos@elegante.com.pe")
        prov4 = Proveedor(numeroDocumento="20778899001", nombreRazonSocial="Calzados y Accesorios Premier", telefono="015554433", direccion="Av. Grau 340, Lima", correoElectronico="comercial@premier.pe")
        db.add_all([prov1, prov2, prov3, prov4])
        
        print("Poblando Clientes...")
        c1 = Cliente(numeroDocumento="12345678", nombres="Maria", apellidos="Lopez", telefono="987654321")
        c2 = Cliente(numeroDocumento="87654321", nombres="Carlos", apellidos="Perez", telefono="999888777")
        c3 = Cliente(numeroDocumento="11223344", nombres="Ana", apellidos="Gomez", telefono="911222333")
        db.add_all([c1, c2, c3])
        
        print("Poblando Categorías...")
        cat_camisas = Categoria(nombreCategoria="Camisas")
        cat_pantalones = Categoria(nombreCategoria="Pantalones")
        cat_accesorios = Categoria(nombreCategoria="Accesorios")
        cat_sacos = Categoria(nombreCategoria="Sacos y Blazers")
        cat_calzado = Categoria(nombreCategoria="Calzado")
        db.add_all([cat_camisas, cat_pantalones, cat_accesorios, cat_sacos, cat_calzado])
        db.flush()

        print("Poblando Productos e Inventario...")
        # Prod 1: Alta rotación, stock saludable
        p1 = Producto(idCategoria=cat_camisas.idCategoria, codigoBarras="CAM-01", nombre="Camisa Oxford Blanca", precioLista=50.00, costoProducto=18.00)
        # Prod 2: Riesgo alto, bajo margen (costo muy alto para probar alerta)
        p2 = Producto(idCategoria=cat_pantalones.idCategoria, codigoBarras="PAN-01", nombre="Jean Clásico Azul", precioLista=45.00, costoProducto=42.00)
        # Prod 3: Agotado / Quiebre Crítico
        p3 = Producto(idCategoria=cat_accesorios.idCategoria, codigoBarras="ACC-01", nombre="Corbata de Seda Negra", precioLista=25.00, costoProducto=6.00)
        # Prod 4: Accesorio normal
        p4 = Producto(idCategoria=cat_accesorios.idCategoria, codigoBarras="ACC-02", nombre="Cinturón de Cuero", precioLista=30.00, costoProducto=10.00)
        # Prod 5: Blazer Alta Rentabilidad, stock crítico
        p5 = Producto(idCategoria=cat_sacos.idCategoria, codigoBarras="SAC-01", nombre="Blazer Slim Fit Gris", precioLista=120.00, costoProducto=45.00)
        # Prod 6: Vestido Elegante, stock crítico
        p6 = Producto(idCategoria=cat_sacos.idCategoria, codigoBarras="VES-01", nombre="Vestido de Noche Elegante", precioLista=95.00, costoProducto=32.00)
        # Prod 7: Calzado de Cuero, stock bajo
        p7 = Producto(idCategoria=cat_calzado.idCategoria, codigoBarras="CAL-01", nombre="Mocasines de Cuero Miel", precioLista=85.00, costoProducto=38.00)
        # Prod 8: Polo Pima, alta rotación
        p8 = Producto(idCategoria=cat_camisas.idCategoria, codigoBarras="POL-01", nombre="Polo Pima Slim Negro", precioLista=35.00, costoProducto=12.00)
        
        db.add_all([p1, p2, p3, p4, p5, p6, p7, p8])
        db.flush()

        # Inventario
        inv1 = Inventario(idProducto=p1.idProducto, cantidadDisponible=40) 
        inv2 = Inventario(idProducto=p2.idProducto, cantidadDisponible=2)  # Quiebre inminente
        inv3 = Inventario(idProducto=p3.idProducto, cantidadDisponible=0)  # Agotado
        inv4 = Inventario(idProducto=p4.idProducto, cantidadDisponible=18) 
        inv5 = Inventario(idProducto=p5.idProducto, cantidadDisponible=3)  # Riesgo Alto
        inv6 = Inventario(idProducto=p6.idProducto, cantidadDisponible=1)  # Riesgo Alto
        inv7 = Inventario(idProducto=p7.idProducto, cantidadDisponible=4)  # Riesgo Alto
        inv8 = Inventario(idProducto=p8.idProducto, cantidadDisponible=55) 
        db.add_all([inv1, inv2, inv3, inv4, inv5, inv6, inv7, inv8])
        
        print("Simulando Ventas Históricas para Analítica y Apriori...")
        now = datetime.now()
        
        # Asociación Apriori: Camisa (p1) + Corbata (p3)
        for i in range(18):
            dias_atras = random.randint(1, 45)
            fecha_venta = now - timedelta(days=dias_atras)
            
            venta = Venta(idCliente=c1.idCliente, idUsuario=u1.idUsuario, montoTotal=75.00, fechaVenta=fecha_venta)
            db.add(venta)
            db.flush()
            
            d1 = DetalleVenta(idVenta=venta.idVenta, idProducto=p1.idProducto, cantidad=1, costoUnitario=p1.costoProducto, precioUnitario=p1.precioLista, subtotal=p1.precioLista)
            d2 = DetalleVenta(idVenta=venta.idVenta, idProducto=p3.idProducto, cantidad=1, costoUnitario=p3.costoProducto, precioUnitario=p3.precioLista, subtotal=p3.precioLista)
            db.add_all([d1, d2])
            
            pago = Pago(idVenta=venta.idVenta, idMedioPago=m1.idMedioPago, montoPagado=75.00, fechaPago=fecha_venta)
            db.add(pago)

        # Asociación Apriori: Blazer (p5) + Camisa (p1)
        for i in range(12):
            dias_atras = random.randint(1, 30)
            fecha_venta = now - timedelta(days=dias_atras)
            
            venta = Venta(idCliente=c2.idCliente, idUsuario=u1.idUsuario, montoTotal=170.00, fechaVenta=fecha_venta)
            db.add(venta)
            db.flush()
            
            d1 = DetalleVenta(idVenta=venta.idVenta, idProducto=p5.idProducto, cantidad=1, costoUnitario=p5.costoProducto, precioUnitario=p5.precioLista, subtotal=p5.precioLista)
            d2 = DetalleVenta(idVenta=venta.idVenta, idProducto=p1.idProducto, cantidad=1, costoUnitario=p1.costoProducto, precioUnitario=p1.precioLista, subtotal=p1.precioLista)
            db.add_all([d1, d2])
            
            pago = Pago(idVenta=venta.idVenta, idMedioPago=m2.idMedioPago, montoPagado=170.00, fechaPago=fecha_venta)
            db.add(pago)

        # Ventas de Jean (p2), Mocasines (p7) y Vestido (p6) para subir su velocidad
        for i in range(15):
            dias_atras = random.randint(1, 25)
            fecha_venta = now - timedelta(days=dias_atras)
            
            venta = Venta(idCliente=c3.idCliente, idUsuario=u2.idUsuario, montoTotal=130.00, fechaVenta=fecha_venta)
            db.add(venta)
            db.flush()
            
            d1 = DetalleVenta(idVenta=venta.idVenta, idProducto=p2.idProducto, cantidad=1, costoUnitario=p2.costoProducto, precioUnitario=p2.precioLista, subtotal=p2.precioLista)
            d2 = DetalleVenta(idVenta=venta.idVenta, idProducto=p7.idProducto, cantidad=1, costoUnitario=p7.costoProducto, precioUnitario=p7.precioLista, subtotal=p7.precioLista)
            db.add_all([d1, d2])
            
            pago = Pago(idVenta=venta.idVenta, idMedioPago=m3.idMedioPago, montoPagado=130.00, fechaPago=fecha_venta)
            db.add(pago)

        print("Simulando Compras Históricas y Estados...")
        compra1 = Compra(idProveedor=prov1.idProveedor, idUsuario=u1.idUsuario, fechaCompra=now - timedelta(days=15), montoTotal=Decimal("450.00"), estado="Completada")
        db.add(compra1)
        db.flush()
        det_c1 = DetalleCompra(idCompra=compra1.idCompra, idProducto=p1.idProducto, cantidad=25, costoUnitario=p1.costoProducto, subtotal=Decimal("450.00"))
        db.add(det_c1)

        print("Poblando Solicitudes de Reposición de Prueba...")
        sol1 = SolicitudReposicion(idProducto=p2.idProducto, cantidad_sugerida=15, motivo="Stock crítico. Riesgo de quiebre inminente.", origen="IA", estado="Pendiente", fecha_creacion=now - timedelta(hours=4))
        sol2 = SolicitudReposicion(idProducto=p3.idProducto, cantidad_sugerida=25, motivo="Producto agotado. Reposición urgente.", origen="IA", estado="Pendiente", fecha_creacion=now - timedelta(hours=1))
        sol3 = SolicitudReposicion(idProducto=p5.idProducto, cantidad_sugerida=10, motivo="Campaña comercial de temporada", origen="Manual", estado="Pendiente", fecha_creacion=now - timedelta(days=1))
        db.add_all([sol1, sol2, sol3])

        db.commit()
        print("¡Base de datos poblada exitosamente con datos ricos de prueba!")
    
    except Exception as e:
        db.rollback()
        print(f"Error poblando BD: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
