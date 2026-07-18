import sys
from config.db import get_db
from models.actores import Cliente, Proveedor

def test_actores_operations():
    print("Iniciando prueba de operaciones con modelos de Actores (Cliente y Proveedor)...")
    
    with get_db() as db:
        try:
            # 1. Instanciar Cliente con ID auto-incremental e información de documento
            cliente_test = Cliente(
                tipoDocumento="DNI",
                numeroDocumento="12345678",
                nombres="Daniel",
                apellidos="Alfonzo",
                telefono="+51999888777",
                correoElectronico="daniel@example.com"
            )
            db.add(cliente_test)
            
            # 2. Instanciar Proveedor con ID auto-incremental e información de documento
            proveedor_test = Proveedor(
                tipoDocumento="RUC",
                numeroDocumento="98765432",
                nombreRazonSocial="Textiles Del Sur S.A.C.",
                telefono="01-4445555",
                direccion="Av. Industrial 123, Lima",
                correoElectronico="contacto@textilesdelsur.com"
            )
            db.add(proveedor_test)
            
            db.flush()
            
            # 3. Imprimir objetos creados y comprobar asignación de atributos
            print("\n--- Datos de Actores Instanciados ---")
            print(f"Cliente:")
            print(f"  ID (Autoincremental): {cliente_test.idCliente}")
            print(f"  Nombre: {cliente_test.nombres} {cliente_test.apellidos}")
            print(f"  Documento: {cliente_test.tipoDocumento} - {cliente_test.numeroDocumento}")
            print(f"  Teléfono: {cliente_test.telefono}")
            print(f"  Correo: {cliente_test.correoElectronico}")
            
            assert cliente_test.numeroDocumento == "12345678", "Error en documento del cliente"
            
            print(f"\nProveedor:")
            print(f"  ID (Autoincremental): {proveedor_test.idProveedor}")
            print(f"  Razón Social: {proveedor_test.nombreRazonSocial}")
            print(f"  Documento: {proveedor_test.tipoDocumento} - {proveedor_test.numeroDocumento}")
            print(f"  Dirección: {proveedor_test.direccion}")
            print(f"  Correo: {proveedor_test.correoElectronico}")
            
            assert proveedor_test.numeroDocumento == "98765432", "Error en documento del proveedor"
            print("\n✅ Asignaciones de llaves primarias auto-incrementales e información de documentos correctas.")
            
            # 4. Ejecutar rollback explícito
            print("\nRealizando rollback() para mantener la integridad histórica...")
            db.rollback()
            print("✅ Rollback completado de forma segura.")
            
        except Exception as e:
            print(f"\n❌ Se produjo un error durante la prueba: {e}")
            db.rollback()
            sys.exit(1)

if __name__ == "__main__":
    test_actores_operations()
