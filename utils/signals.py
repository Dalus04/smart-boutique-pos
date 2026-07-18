from PySide6.QtCore import QObject, Signal

class AppSignals(QObject):
    cliente_actualizado = Signal()
    proveedor_actualizado = Signal()
    inventario_actualizado = Signal()

# Instancia global del bus de eventos
global_signals = AppSignals()
