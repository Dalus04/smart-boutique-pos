import sys
import os
from datetime import date, timedelta
from decimal import Decimal

# Añadir el directorio raíz al path para que las importaciones funcionen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models.base import Base

import models.actores
import models.catalogo
import models.usuarios
import models.pos
import models.suministro

from models.pos import Venta, DetalleVenta
from models.suministro import Inventario
from services.prediccion import PrediccionService

def test_prediccion_riesgo():
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        print("--- Iniciando Prueba de Predicción de Riesgo ---")
        
        # 1. Simulación (Arrange)
        print("Creando ventas simuladas para los últimos 30 días...")
        id_prod = 1
        dias_simulacion = 30
        hoy = date.today()
        
        # Simular ventas: 2 unidades diarias vendidas de manera constante
        for i in range(dias_simulacion):
            fecha_venta = hoy - timedelta(days=i)
            venta = Venta(idUsuario=1, fechaVenta=fecha_venta, montoTotal=Decimal('40.00'))
            session.add(venta)
            session.flush()
            
            detalle = DetalleVenta(
                idVenta=venta.idVenta,
                idProducto=id_prod,
                cantidad=2,
                costoUnitario=Decimal('10.00'),
                precioUnitario=Decimal('20.00'),
                subtotal=Decimal('40.00')
            )
            session.add(detalle)
            
        # Simular stock de inventario
        # Inicialmente insertamos 30 de stock repartido en dos registros para validar el func.sum()
        inv = Inventario(idProducto=id_prod, fechaActualizacion=hoy, cantidadDisponible=30)
        session.add(inv)
        session.commit()
        
        # 2. Extracción de velocidad (Act - Feature)
        velocidad = PrediccionService.calcular_velocidad_venta(session, id_prod, dias=30)
        print(f"Velocidad de venta calculada: {velocidad} unidades/día (Esperado: 2.0)")
        assert velocidad == 2.0, f"Error en cálculo de velocidad, obtenido: {velocidad}"
        
        # 3. Clasificación (Act & Assert)
        dias_entrega = 5
        print(f"\nProbando clasificación con días de entrega = {dias_entrega}...")
        
        # Caso 1: Stock 30. Demanda = 2.0 * 5 = 10. Factor seguridad = 10 * 1.5 = 15.
        # Stock (30) > 15 -> 'Sin Riesgo'
        riesgo = PrediccionService.clasificar_riesgo_quiebre(30, velocidad, dias_entrega)
        print(f"Prueba con Stock = 30 -> Riesgo: {riesgo}")
        assert riesgo == 'Sin Riesgo'
        
        # Caso 2: Stock 12. Demanda = 10. 10 < 12 <= 15 -> 'Riesgo Medio'
        riesgo = PrediccionService.clasificar_riesgo_quiebre(12, velocidad, dias_entrega)
        print(f"Prueba con Stock = 12 -> Riesgo: {riesgo}")
        assert riesgo == 'Riesgo Medio'
        
        # Caso 3: Stock 8. Demanda = 10. 8 <= 10 -> 'Riesgo Alto'
        riesgo = PrediccionService.clasificar_riesgo_quiebre(8, velocidad, dias_entrega)
        print(f"Prueba con Stock = 8  -> Riesgo: {riesgo}")
        assert riesgo == 'Riesgo Alto'
        
        # Evaluando el método completo con la BD
        print("\nEvaluando el orquestador evaluar_producto() usando la base de datos (Stock actual: 30)...")
        reporte = PrediccionService.evaluar_producto(session, id_prod, dias_entrega)
        print(reporte)
        assert reporte['riesgo'] == 'Sin Riesgo'
        assert reporte['stock_actual'] == 30
        
        # 4. Limpieza (Rollback)
        session.rollback()
        print("\n✅ Prueba de predicción ejecutada exitosamente. El rollback() final fue llamado.")

if __name__ == '__main__':
    test_prediccion_riesgo()
