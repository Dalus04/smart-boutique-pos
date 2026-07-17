import sys
from decimal import Decimal
from config.db import get_db
from models.catalogo import Categoria, Producto

def test_catalogo_operations():
    print("Iniciando prueba de operaciones de catálogo y margen de rentabilidad...")
    
    with get_db() as db:
        try:
            # 1. Crear una nueva Categoría (transacción activa)
            categoria_test = Categoria(nombreCategoria="Categoría de Prueba")
            db.add(categoria_test)
            db.flush() # Asignar ID temporalmente sin hacer commit
            
            print(f"✅ Categoría creada: {categoria_test.nombreCategoria} (ID temporal: {categoria_test.idCategoria})")
            
            # 2. Crear un Producto con margen normal
            producto_normal = Producto(
                categoria=categoria_test,
                nombre="Camisa Casual",
                talla="M",
                color="Azul",
                marca="Boutique Brand",
                material="Algodón",
                costoProducto=Decimal("60.00"),
                precioLista=Decimal("100.00")
            )
            db.add(producto_normal)
            
            # 3. Crear un Producto con precio de lista cero (para probar división por cero)
            producto_cero = Producto(
                categoria=categoria_test,
                nombre="Producto Promocional Gratuito",
                talla="N/A",
                color="N/A",
                marca="Boutique Brand",
                material="N/A",
                costoProducto=Decimal("10.00"),
                precioLista=Decimal("0.00")
            )
            db.add(producto_cero)
            db.flush()
            
            # 4. Probar cálculos del margen de rentabilidad
            print("\n--- Resultados de Margen de Rentabilidad ---")
            print(f"Producto: {producto_normal.nombre}")
            print(f"  Costo: ${producto_normal.costoProducto}")
            print(f"  Precio de Venta: ${producto_normal.precioLista}")
            print(f"  Margen calculado: {producto_normal.margen_rentabilidad:.2f}%")
            
            # Verificación del margen normal (debe ser 40.00%)
            assert abs(producto_normal.margen_rentabilidad - 40.00) < 0.001, "Error en cálculo de margen normal"
            print("  ✅ Cálculo de margen normal correcto.")
            
            print(f"Producto: {producto_cero.nombre}")
            print(f"  Costo: ${producto_cero.costoProducto}")
            print(f"  Precio de Venta: ${producto_cero.precioLista}")
            print(f"  Margen calculado: {producto_cero.margen_rentabilidad:.2f}%")
            
            # Verificación de división por cero (debe ser 0.00%)
            assert producto_cero.margen_rentabilidad == 0.0, "Error en manejo de división por cero"
            print("  ✅ Manejo de división por cero correcto.")
            
            # 5. Ejecutar rollback explícito
            print("\nRealizando rollback() para mantener la integridad histórica...")
            db.rollback()
            print("✅ Rollback completado de forma segura.")
            
        except Exception as e:
            print(f"\n❌ Se produjo un error durante la prueba: {e}")
            db.rollback()
            sys.exit(1)

if __name__ == "__main__":
    test_catalogo_operations()
