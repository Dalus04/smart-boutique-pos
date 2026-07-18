import sys
import datetime
from decimal import Decimal
from config.db import get_db
from models.usuarios import Usuario
from models.catalogo import Categoria, Producto
from models.actores import Cliente
from models.pos import Venta, DetalleVenta, MedioPago, Pago
import models.suministro

def test_pos_operations():
    print("Iniciando prueba de operaciones de Punto de Venta (POS)...")
    
    with get_db() as db:
        try:
            # 1. Crear Usuario vendedor
            usuario = Usuario(
                nombres="Vendedor Principal",
                apellidos="Pérez",
                nombreUsuario="vendedor_pos",
                contrasena="vendedor_pass",
                rol="Cajero",
                estado="Activo"
            )
            db.add(usuario)
            db.flush()
            print(f"✅ Vendedor creado: {usuario.nombreUsuario} (ID: {usuario.idUsuario})")
            
            # 2. Crear Cliente (ID auto-incremental con tipo/nro de documento)
            cliente = Cliente(
                tipoDocumento="DNI",
                numeroDocumento="77665544",
                nombres="María Alejandra",
                apellidos="López",
                telefono="+51988776655",
                correoElectronico="maria.lopez@example.com"
            )
            db.add(cliente)
            db.flush()
            print(f"✅ Cliente creado: {cliente.nombres} {cliente.apellidos} (ID: {cliente.idCliente})")
            
            # 3. Crear Categoría y Productos
            categoria = Categoria(nombreCategoria="Ropa de Estación")
            db.add(categoria)
            db.flush()
            
            producto1 = Producto(
                categoria=categoria,
                nombre="Casaca de Invierno",
                talla="L",
                color="Negro",
                marca="WinterStyle",
                material="Plumas",
                costoProducto=Decimal("120.00"),
                precioLista=Decimal("200.00")
            )
            producto2 = Producto(
                categoria=categoria,
                nombre="Chompa de Lana",
                talla="M",
                color="Gris",
                marca="WoolCo",
                material="Lana",
                costoProducto=Decimal("45.00"),
                precioLista=Decimal("80.00")
            )
            db.add(producto1)
            db.add(producto2)
            db.flush()
            print(f"✅ Productos creados: {producto1.nombre} y {producto2.nombre}")
            
            # 4. Crear Medio de Pago
            medio_pago = MedioPago(nombreMedioPago="Tarjeta de Débito")
            db.add(medio_pago)
            db.flush()
            print(f"✅ Medio de pago creado: {medio_pago.nombreMedioPago} (ID: {medio_pago.idMedioPago})")
            
            # 5. Crear Venta y Detalles de Venta
            venta = Venta(
                cliente=cliente,
                usuario=usuario,
                fechaVenta=datetime.datetime.utcnow(),
                montoTotal=Decimal("640.00")
            )
            db.add(venta)
            db.flush()
            
            detalle1 = DetalleVenta(
                venta=venta,
                producto=producto1,
                cantidad=2,
                costoUnitario=Decimal("120.00"),
                precioUnitario=Decimal("200.00"),
                subtotal=Decimal("400.00")
            )
            detalle2 = DetalleVenta(
                venta=venta,
                producto=producto2,
                cantidad=3,
                costoUnitario=Decimal("45.00"),
                precioUnitario=Decimal("80.00"),
                subtotal=Decimal("240.00")
            )
            db.add(detalle1)
            db.add(detalle2)
            db.flush()
            
            # 6. Crear Pago asociado
            pago = Pago(
                venta=venta,
                medio_pago=medio_pago,
                fechaPago=datetime.datetime.utcnow(),
                montoPagado=Decimal("640.00")
            )
            db.add(pago)
            db.flush()
            print(f"✅ Venta registrada e Pago asociado creados con éxito.")
            print(f"   Venta ID: {venta.idVenta}, Monto Total: ${venta.montoTotal}")
            print(f"   Pago ID: {pago.idPago}, Monto Pagado: ${pago.montoPagado}")
            
            # 7. Verificar propiedad total_articulos
            print("\n--- Verificación de la Propiedad total_articulos en Venta ---")
            print(f"Venta ID: {venta.idVenta}")
            print(f"  Detalle 1: {detalle1.cantidad} unidades de '{producto1.nombre}'")
            print(f"  Detalle 2: {detalle2.cantidad} unidades de '{producto2.nombre}'")
            print(f"  Total de Artículos Calculado: {venta.total_articulos}")
            
            assert venta.total_articulos == 5, f"Error: Se esperaba 5 pero se obtuvo {venta.total_articulos}"
            print("✅ El cálculo de 'total_articulos' fue exitoso y correcto.")
            
            # 8. Ejecutar rollback() obligatorio para mantener limpia la base de datos
            print("\nRealizando rollback() para mantener la integridad histórica...")
            db.rollback()
            print("✅ Rollback completado de forma segura. La base de datos no fue modificada.")
            
        except Exception as e:
            print(f"\n❌ Se produjo un error durante la prueba: {e}")
            db.rollback()
            sys.exit(1)

if __name__ == "__main__":
    test_pos_operations()
