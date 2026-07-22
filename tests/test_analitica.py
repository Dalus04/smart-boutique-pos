import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import datetime
from decimal import Decimal
from sqlalchemy import select
from config.db import get_db
from models.usuarios import Usuario
from models.catalogo import Categoria, Producto
from models.actores import Cliente
from models.suministro import Inventario
from models.pos import Venta, DetalleVenta, MedioPago, Pago
import models.suministro 
from services.analitica import AnaliticaService

def test_analitica_kpis():
    print("Iniciando prueba de KPIs del Servicio de Analítica...")
    
    with get_db() as db:
        try:
            # 1. Crear Usuario y Cliente con nombres únicos para aislar la prueba
            usuario = Usuario(
                nombres="Analista Comercial Test",
                apellidos="Díaz",
                nombreUsuario="analista_comercial_test",
                contrasena="analista_pass",
                rol="Supervisor",
                estado="Activo"
            )
            db.add(usuario)
            db.flush()
            
            cliente = Cliente(
                tipoDocumento="DNI",
                numeroDocumento="88776655",
                nombres="Andrés Manuel",
                apellidos="Rivera Test",
                telefono="+51966554433",
                correoElectronico="andres.rivera.test@example.com"
            )
            db.add(cliente)
            db.flush()
            
            # 2. Crear dos Categorías con nombres únicos para aislar las métricas de rentabilidad
            cat_calzado = Categoria(nombreCategoria="Calzado de Prueba Analitica")
            cat_ropa = Categoria(nombreCategoria="Ropa de Prueba Analitica")
            db.add(cat_calzado)
            db.add(cat_ropa)
            db.flush()
            
            # 3. Crear Productos
            prod_zap = Producto(
                categoria=cat_calzado,
                nombre="Zapatos Formales Test",
                talla="41",
                color="Marrón",
                marca="LeatherCo",
                material="Cuero",
                costoProducto=Decimal("60.00"),
                precioLista=Decimal("100.00")
            )
            prod_tenis = Producto(
                categoria=cat_calzado,
                nombre="Zapatillas Urbanas Test",
                talla="40",
                color="Blanco",
                marca="StreetBrand",
                material="Lona",
                costoProducto=Decimal("40.00"),
                precioLista=Decimal("50.00")
            )
            prod_abrigo = Producto(
                categoria=cat_ropa,
                nombre="Abrigo de Lana Premium Test",
                talla="XL",
                color="Gris",
                marca="LuxuryWool",
                material="Lana",
                costoProducto=Decimal("80.00"),
                precioLista=Decimal("200.00")
            )
            db.add(prod_zap)
            db.add(prod_tenis)
            db.add(prod_abrigo)
            db.flush()
            
            # 4. Crear Inventarios para probar "Salud de Inventario"
            inv1 = Inventario(producto=prod_zap, fechaActualizacion=datetime.datetime.utcnow(), cantidadDisponible=3)
            inv2 = Inventario(producto=prod_tenis, fechaActualizacion=datetime.datetime.utcnow(), cantidadDisponible=12)
            inv3 = Inventario(producto=prod_abrigo, fechaActualizacion=datetime.datetime.utcnow(), cantidadDisponible=25)
            db.add(inv1)
            db.add(inv2)
            db.add(inv3)
            db.flush()
            
            # 5. Registrar Medio de Pago único
            medio_pago = MedioPago(nombreMedioPago="Efectivo de Prueba Analitica")
            db.add(medio_pago)
            db.flush()
            
            # 6. Registrar Ventas en distintas fechas para probar "Tendencia de Ventas" y "Ranking de Productos"
            # Venta 1: Mayo 2026 -> 5 Zapatos Formales ($100 c/u) = $500 total
            v1 = Venta(cliente=cliente, usuario=usuario, fechaVenta=datetime.datetime(2026, 5, 15, 12, 0, 0), montoTotal=Decimal("500.00"))
            db.add(v1)
            db.flush()
            det1 = DetalleVenta(venta=v1, producto=prod_zap, cantidad=5, costoUnitario=Decimal("60.00"), precioUnitario=Decimal("100.00"), subtotal=Decimal("500.00"))
            db.add(det1)
            p1 = Pago(venta=v1, medio_pago=medio_pago, fechaPago=datetime.datetime(2026, 5, 15, 12, 0, 0), montoPagado=Decimal("500.00"))
            db.add(p1)
            
            # Venta 2: Junio 2026 -> 10 Zapatillas Urbanas ($50 c/u) = $500 total
            v2 = Venta(cliente=cliente, usuario=usuario, fechaVenta=datetime.datetime(2026, 6, 20, 12, 0, 0), montoTotal=Decimal("500.00"))
            db.add(v2)
            db.flush()
            det2 = DetalleVenta(venta=v2, producto=prod_tenis, cantidad=10, costoUnitario=Decimal("40.00"), precioUnitario=Decimal("50.00"), subtotal=Decimal("500.00"))
            db.add(det2)
            p2 = Pago(venta=v2, medio_pago=medio_pago, fechaPago=datetime.datetime(2026, 6, 20, 12, 0, 0), montoPagado=Decimal("500.00"))
            db.add(p2)
            
            # Venta 3: Julio 2026 -> 2 Abrigos de Lana ($200 c/u) = $400 total
            v3 = Venta(cliente=cliente, usuario=usuario, fechaVenta=datetime.datetime(2026, 7, 10, 12, 0, 0), montoTotal=Decimal("400.00"))
            db.add(v3)
            db.flush()
            det3 = DetalleVenta(venta=v3, producto=prod_abrigo, cantidad=2, costoUnitario=Decimal("80.00"), precioUnitario=Decimal("200.00"), subtotal=Decimal("400.00"))
            db.add(det3)
            p3 = Pago(venta=v3, medio_pago=medio_pago, fechaPago=datetime.datetime(2026, 7, 10, 12, 0, 0), montoPagado=Decimal("400.00"))
            db.add(p3)
            
            db.flush()
            print("✅ Datos transaccionales y de inventario simulados creados correctamente.")
            
            # PRUEBA KPI 1: Salud de Inventario
            print("\n--- KPI 1: Salud de Inventario ---")
            salud = AnaliticaService.obtener_salud_inventario(db)
            print(f"Salud del Inventario: {salud}")
            
            assert salud["Crítico"]["items"] >= 1 and salud["Crítico"]["unidades"] >= 3, "Error en salud Crítico"
            assert salud["Bajo"]["items"] >= 1 and salud["Bajo"]["unidades"] >= 12, "Error en salud Bajo"
            assert salud["Óptimo"]["items"] >= 1 and salud["Óptimo"]["unidades"] >= 25, "Error en salud Óptimo"
            print("✅ KPI 1: Salud de Inventario computado correctamente.")
            
            # PRUEBA KPI 2: Rentabilidad por Categoría
            print("\n--- KPI 2: Rentabilidad por Categoría ---")
            rentabilidades = AnaliticaService.obtener_rentabilidad_por_categoria(db)
            calzado_checked = False
            ropa_checked = False
            for r in rentabilidades:
                if r["categoria"] == "Calzado de Prueba Analitica":
                    print(f"Categoría: '{r['categoria']}' | Margen Ponderado: {r['margen_ponderado']}%")
                    assert abs(r["margen_ponderado"] - 30.00) < 0.01, f"Error Calzado margen: {r['margen_ponderado']}"
                    calzado_checked = True
                elif r["categoria"] == "Ropa de Prueba Analitica":
                    print(f"Categoría: '{r['categoria']}' | Margen Ponderado: {r['margen_ponderado']}%")
                    assert abs(r["margen_ponderado"] - 60.00) < 0.01, f"Error Ropa margen: {r['margen_ponderado']}"
                    ropa_checked = True
            
            assert calzado_checked and ropa_checked, "No se encontraron las categorías de prueba en la rentabilidad"
            print("✅ KPI 2: Rentabilidad por Categoría computada correctamente.")
            
            # PRUEBA KPI 3: Tendencia de Ventas
            print("\n--- KPI 3: Tendencia de Ventas (Mensual) ---")
            tendencia = AnaliticaService.obtener_tendencia_ventas(db)
            for t in tendencia:
                print(f"Mes: {t['mes']} | Total Vendido: ${t['total_vendido']} | Transacciones: {t['transacciones']}")
            
            meses_map = {t["mes"]: t["total_vendido"] for t in tendencia}
            assert meses_map["2026-05"] >= 500.0, "Error tendencia mayo"
            assert meses_map["2026-06"] >= 500.0, "Error tendencia junio"
            assert meses_map["2026-07"] >= 400.0, "Error tendencia julio"
            print("✅ KPI 3: Tendencia de Ventas computada correctamente.")
            
            # PRUEBA KPI 4: Ranking de Productos
            print("\n--- Ranking de Productos ---")
            ranking = AnaliticaService.obtener_ranking_productos(
                db, 
                limit=100, 
                fecha_inicio=datetime.date(2026, 1, 1), 
                fecha_fin=datetime.date(2026, 12, 31)
            )
            for index, p in enumerate(ranking, 1):
                print(f"Puesto {index}: '{p['nombre']}' | Cantidad vendida: {p['cantidad_vendida']} | Recaudado: ${p['total_recaudado']}")
            
            productos_vendidos = {p["nombre"]: p["cantidad_vendida"] for p in ranking}
            assert productos_vendidos["Zapatillas Urbanas Test"] >= 10
            assert productos_vendidos["Zapatos Formales Test"] >= 5
            assert productos_vendidos["Abrigo de Lana Premium Test"] >= 2
            print("✅ KPI 4: Ranking de Productos computado correctamente.")
            
            # Rollback explícito obligatorio para no alterar la base de datos local
            print("\nRealizando rollback() para mantener la integridad histórica...")
            db.rollback()
            print("✅ Rollback completado de forma segura. La base de datos no fue modificada.")
            print("\n🎉 ¡Todas las pruebas de analítica y KPIs pasaron exitosamente!")
            
        except Exception as e:
            print(f"\n❌ Se produjo un error durante la prueba de analítica: {e}")
            db.rollback()
            sys.exit(1)

run_analytics_tests = test_analitica_kpis

if __name__ == "__main__":
    test_analitica_kpis()
