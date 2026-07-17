import sys
import os
from datetime import date
from decimal import Decimal

# Añadir el directorio raíz al path para que las importaciones funcionen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models.base import Base
# Importar todos los modelos para que Base.metadata.create_all los reconozca
from models.pos import Venta, DetalleVenta
import models.actores
import models.catalogo
import models.usuarios
import models.pos
import models.suministro
from services.mineria import MineriaService

def test_sugerencia_venta_cruzada():
    # Usar una base de datos SQLite en memoria para la prueba
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        print("--- Iniciando Prueba de Minería de Datos ---")
        
        # 1. Simulación (Arrange)
        print("Creando ventas simuladas...")
        # Simular 5 ventas donde los productos 1 y 2 siempre se compran juntos
        # y los productos 3 y 4 también se compran juntos en un par de ocasiones.
        transacciones_simuladas = [
            [1, 2, 3], # Venta 1
            [1, 2],    # Venta 2
            [1, 2, 4], # Venta 3
            [1, 2],    # Venta 4
            [3, 4],    # Venta 5
        ]
        
        for idx, t_prods in enumerate(transacciones_simuladas, start=1):
            venta = Venta(idUsuario=1, fechaVenta=date.today(), montoTotal=Decimal('100.00'))
            session.add(venta)
            session.flush() # Para obtener idVenta
            
            for p_id in t_prods:
                detalle = DetalleVenta(
                    idVenta=venta.idVenta,
                    idProducto=p_id,
                    cantidad=1,
                    costoUnitario=Decimal('10.00'),
                    precioUnitario=Decimal('20.00'),
                    subtotal=Decimal('20.00')
                )
                session.add(detalle)
        
        session.commit() # Asegurar que se guardaron temporalmente en la BD en memoria
        
        # 2. Entrenamiento (Act)
        print("Entrenando modelo Apriori...")
        # Con min_support=2 y min_confidence=0.5 (por defecto)
        MineriaService.entrenar_modelo(session, min_support=2, min_confidence=0.5)
        
        print("Reglas generadas en memoria:")
        for ant, cons_list in MineriaService._reglas.items():
            print(f"  Producto {ant} sugiere: {cons_list}")
            
        # 3. Predicción (Assert)
        print("\nProbando sugerencia...")
        # Si el carrito tiene el producto 1, debería sugerir fuertemente el producto 2
        carrito = [1]
        sugerencias = MineriaService.sugerir_venta_cruzada(carrito)
        print(f"Carrito actual: {carrito}")
        print(f"Sugerencias recibidas: {sugerencias}")
        
        assert 2 in sugerencias, "La sugerencia falló: el Producto 2 debería estar recomendado para el Producto 1."
        assert sugerencias[0] == 2, "El Producto 2 debería ser la recomendación número 1."
        
        # Simulamos un carrito con el producto 3
        carrito_2 = [3]
        sugerencias_2 = MineriaService.sugerir_venta_cruzada(carrito_2)
        print(f"Carrito actual: {carrito_2}")
        print(f"Sugerencias recibidas: {sugerencias_2}")
        
        # 4. Limpieza (Rollback) - Aunque es in-memory, hacemos rollback como buena práctica/requerimiento
        session.rollback()
        print("\n✅ Prueba ejecutada exitosamente. El rollback() final fue llamado.")

if __name__ == '__main__':
    test_sugerencia_venta_cruzada()
