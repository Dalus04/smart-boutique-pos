import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from config.db import engine, get_db

def test_db_connection():
    print("Iniciando prueba de conexión a la base de datos...")
    
    try:
        # 1. Probar conexión directa a través del motor
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                print("✅ Conexión exitosa del motor (engine.connect() funcionó correctamente).")
            else:
                print("⚠️ El motor se conectó, pero retornó un resultado inesperado.")
                sys.exit(1)
                
        # 2. Probar la fábrica de sesiones transaccionales
        with get_db() as db:
            # Ejecutar una consulta básica usando la sesión
            result = db.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                print("✅ Sesión transaccional instanciada y ejecutada con éxito (get_db() funcionó correctamente).")
            else:
                print("⚠️ La sesión se inició, pero retornó un resultado inesperado.")
                sys.exit(1)
                
        print("\n🎉 ¡Todas las pruebas de conexión pasaron exitosamente!")
        
    except Exception as e:
        print("\n❌ Error al conectar a la base de datos:")
        print(f"Detalle del error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_db_connection()
