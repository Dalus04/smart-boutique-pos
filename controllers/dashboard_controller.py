from PySide6.QtCore import QObject, QThread, Signal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import datetime

from views.dashboard_view import DashboardView
from config.db import SessionLocal
from services.analitica import AnaliticaService

class AnaliticaWorker(QThread):
    # Definimos señales para enviar los datos de vuelta al hilo principal
    datos_cargados = Signal(dict, list)  # salud_inventario, tendencia_ventas
    error = Signal(str)

    def run(self):
        # Crear una sesión local exclusiva para este hilo
        db = SessionLocal()
        try:
            # Obtener KPIs
            salud = AnaliticaService.obtener_salud_inventario(db)
            
            # Obtener tendencia de ventas
            tendencia = AnaliticaService.obtener_tendencia_ventas(db)
            
            self.datos_cargados.emit(salud, tendencia)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            db.close()

class DashboardController(QObject):
    def __init__(self):
        super().__init__()
        self.view = DashboardView()
        self.worker = None

    def start(self):
        """ Inicia el worker para cargar datos de forma asíncrona sin bloquear la UI """
        # Evitar crear múltiples workers al mismo tiempo
        if self.worker and self.worker.isRunning():
            return
            
        self.view.chart_placeholder.setText("Calculando métricas en segundo plano...")
        self.worker = AnaliticaWorker()
        self.worker.datos_cargados.connect(self._on_datos_cargados)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_datos_cargados(self, salud_inventario, tendencia_ventas):
        # Actualizar KPIs
        items_criticos = salud_inventario.get("Crítico", {}).get("items", 0)
        unidades_optimo = salud_inventario.get("Óptimo", {}).get("unidades", 0)
        total_trx = sum([t.get("transacciones", 0) for t in tendencia_ventas])

        self.view.lbl_salud_inv.setText(str(items_criticos))
        self.view.lbl_unidades_inv.setText(str(unidades_optimo))
        self.view.lbl_total_ventas.setText(str(total_trx))

        # Dibujar gráfico de barras en el canvas
        self._render_chart(tendencia_ventas)

    def _on_error(self, error_msg):
        self.view.chart_placeholder.setText(f"Error al cargar datos: {error_msg}")
        self.view.lbl_salud_inv.setText("Error")
        self.view.lbl_unidades_inv.setText("Error")
        self.view.lbl_total_ventas.setText("Error")

    def _render_chart(self, tendencia_ventas):
        # Limpiar el layout por si había widgets o layouts viejos
        for i in reversed(range(self.view.chart_layout.count())): 
            widget_to_remove = self.view.chart_layout.itemAt(i).widget()
            self.view.chart_layout.removeWidget(widget_to_remove)
            if widget_to_remove:
                widget_to_remove.setParent(None)

        # Si no hay datos, mostrar algo base
        if not tendencia_ventas:
            meses = ['Sin datos']
            totales = [0]
        else:
            meses = [t["mes"] for t in tendencia_ventas]
            totales = [t["total_vendido"] for t in tendencia_ventas]

        # Crear figura
        fig = Figure(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor('#121212') # Color de fondo oscuro (Dark Theme)

        ax = fig.add_subplot(111)
        ax.set_facecolor('#1e1e1e')
        ax.tick_params(colors='white')
        
        # Darle color sutil a los bordes
        for spine in ax.spines.values():
            spine.set_color('#333333')
            
        ax.grid(color='#2d2d2d', linestyle='-', linewidth=0.5, axis='y', alpha=0.5)
        
        ax.set_title('Tendencia de Recaudación por Mes', color='white', pad=15)

        # Plotear barras
        bars = ax.bar(meses, totales, color='#2a82da')
        ax.set_ylabel('Total Vendido ($)', color='white')

        # Ajustar rotación y tamaño para legibilidad
        ax.tick_params(axis='x', labelrotation=45, labelsize=8)
        
        # Ocultar etiquetas intermedias si hay demasiados meses para evitar amontonamiento
        if len(meses) > 12:
            step = len(meses) // 8  # Mostrar alrededor de 8-10 etiquetas principales
            for idx, label in enumerate(ax.xaxis.get_ticklabels()):
                if idx % step != 0 and idx != len(meses) - 1: # Mantener la última etiqueta siempre visible
                    label.set_visible(False)

        fig.tight_layout()

        # Insertar canvas en el UI
        canvas = FigureCanvas(fig)
        self.view.chart_layout.addWidget(canvas)

        # Guardar referencias para el evento hover
        self.bars = list(bars)
        self.meses_data = meses
        canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _on_hover(self, event):
        if event.inaxes is None or not hasattr(self, 'bars'):
            return
        
        from PySide6.QtWidgets import QToolTip
        from PySide6.QtGui import QCursor
        
        for idx, bar in enumerate(self.bars):
            cont, _ = bar.contains(event)
            if cont:
                mes = self.meses_data[idx]
                total = bar.get_height()
                tooltip_text = f"<b>Mes:</b> {mes}<br><b>Total:</b> ${total:,.2f}"
                
                # Mostrar el tooltip en la posición actual del cursor de forma inmediata
                QToolTip.showText(QCursor.pos(), tooltip_text, self.view)
                return

