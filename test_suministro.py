import sys
import datetime
from decimal import Decimal
from config.db import get_db
from models.usuarios import Administrador, Usuario
from models.catalogo import Categoria, Producto
from models.actores import Proveedor
from models.suministro import Inventario, Compra, DetalleCompra

def test_suministro_and_usuarios():
    print("Iniciando prueba de operaciones de Suministro y Usuarios...")
    
    with get_db() as db:
        try:
            # 1. Crear Administrador y Usuario
            admin = Administrador(
                nombres="Administrador de Prueba",
                usuario="admin_test",
                contrasena="admin_pass_123"
            )
            db.add(admin)
            db.flush()
            print(f"✅ Administrador creado: {admin.usuario} (ID: {admin.idAdministrador})")
            
            usuario = Usuario(
                administrador=admin,
                nombres="Usuario Suministro",
                apellidos="De Prueba",
                nombreUsuario="user_suministro",
                contrasena="user_pass_123",
                rol="Comprador",
                estado="Activo"
            )
            db.add(usuario)
            db.flush()
            print(f"✅ Usuario creado: {usuario.nombreUsuario} (ID: {usuario.idUsuario})")
            
            # 2. Crear Categoria y Producto
            categoria = Categoria(nombreCategoria="Calzado Deportivo")
            db.add(categoria)
            db.flush()
            
            producto = Producto(
                categoria=categoria,
                nombre="Zapatillas Running",
                talla="42",
                color="Rojo",
                marca="SportBrand",
                material="Sintético",
                costoProducto=Decimal("80.00"),
                precioLista=Decimal("120.00")
            )
            db.add(producto)
            db.flush()
            print(f"✅ Producto creado: {producto.nombre} (ID: {producto.idProducto})")
            
            # 3. Crear Proveedor (Llave primaria manual dentro del rango de INT 32 bits)
            proveedor = Proveedor(
                idProveedor=99887766,
                nombreRazonSocial="Importaciones Running S.A.C.",
                telefono="01-5556666",
                direccion="Av. Principal 456, Lima",
                correoElectronico="ventas@importacionesrunning.com"
            )
            db.add(proveedor)
            db.flush()
            print(f"✅ Proveedor creado: {proveedor.nombreRazonSocial} (ID Manual: {proveedor.idProveedor})")
            
            # 4. Crear Compra con su DetalleCompra asociado
            compra = Compra(
                proveedor=proveedor,
                usuario=usuario,
                fechaCompra=datetime.date.today(),
                montoTotal=Decimal("800.00")
            )
            db.add(compra)
            db.flush()
            
            detalle_compra = DetalleCompra(
                compra=compra,
                producto=producto,
                cantidad=10,
                costoUnitario=Decimal("80.00"),
                subtotal=Decimal("800.00")
            )
            db.add(detalle_compra)
            db.flush()
            print(f"✅ Compra e historiales de DetalleCompra creados con éxito.")
            print(f"   Compra ID: {compra.idCompra}, Monto Total: ${compra.montoTotal}")
            print(f"   DetalleCompra ID: {detalle_compra.idDetalleCompra}, Cantidad: {detalle_compra.cantidad}, Subtotal: ${detalle_compra.subtotal}")
            
            # 5. Instanciar y verificar los 3 estados de stock en Inventario
            print("\n--- Verificación de la Propiedad estado_stock en Inventario ---")
            
            # Estado Crítico (cantidadDisponible <= 5)
            inv_critico = Inventario(
                producto=producto,
                fechaActualizacion=datetime.date.today(),
                cantidadDisponible=3
            )
            print(f"Stock: {inv_critico.cantidadDisponible} -> Estado esperado: Crítico | Estado calculado: '{inv_critico.estado_stock}'")
            assert inv_critico.estado_stock == "Crítico", f"Error: Se esperaba 'Crítico' pero se obtuvo '{inv_critico.estado_stock}'"
            
            # Estado Bajo (cantidadDisponible <= 15)
            inv_bajo = Inventario(
                producto=producto,
                fechaActualizacion=datetime.date.today(),
                cantidadDisponible=12
            )
            print(f"Stock: {inv_bajo.cantidadDisponible} -> Estado esperado: Bajo | Estado calculado: '{inv_bajo.estado_stock}'")
            assert inv_bajo.estado_stock == "Bajo", f"Error: Se esperaba 'Bajo' pero se obtuvo '{inv_bajo.estado_stock}'"
            
            # Estado Óptimo (cantidadDisponible > 15)
            inv_optimo = Inventario(
                producto=producto,
                fechaActualizacion=datetime.date.today(),
                cantidadDisponible=25
            )
            print(f"Stock: {inv_optimo.cantidadDisponible} -> Estado esperado: Óptimo | Estado calculado: '{inv_optimo.estado_stock}'")
            assert inv_optimo.estado_stock == "Óptimo", f"Error: Se esperaba 'Óptimo' pero se obtuvo '{inv_optimo.estado_stock}'"
            
            print("✅ Los tres estados del stock se calcularon rigurosamente de forma correcta.")
            
            # 6. Ejecutar rollback() obligatorio
            print("\nRealizando rollback() para mantener la integridad histórica...")
            db.rollback()
            print("✅ Rollback completado de forma segura. La base de datos no fue modificada.")
            
        except Exception as e:
            print(f"\n❌ Se produjo un error durante la prueba: {e}")
            db.rollback()
            sys.exit(1)

if __name__ == "__main__":
    test_suministro_and_usuarios()
