from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from utils.ui_helpers import crear_tarjeta_kpi

class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        
        # Título
        self.title_label = QLabel("Dashboard Analítico")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #ffffff;")
        self.main_layout.addWidget(self.title_label)
        
        # Contenedor de KPIs
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(20)
        
        # Tarjetas de KPIs
        frame1, self.lbl_salud_inv = crear_tarjeta_kpi("Items Críticos (Inventario)", "Cargando...", "#d9534f")
        self.kpi_layout.addWidget(frame1)
        
        frame2, self.lbl_unidades_inv = crear_tarjeta_kpi("Unidades (Óptimo)", "Cargando...", "#2e7d32")
        self.kpi_layout.addWidget(frame2)
        
        frame3, self.lbl_total_ventas = crear_tarjeta_kpi("Total Transacciones", "Cargando...", "#2a82da")
        self.kpi_layout.addWidget(frame3)
        
        self.main_layout.addLayout(self.kpi_layout)
        
        # Contenedor Inferior para Gráfico
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chart_placeholder = QLabel("Cargando métricas y gráficos...")
        self.chart_placeholder.setStyleSheet("color: #a0a0a0; font-size: 16px; font-style: italic;")
        self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_layout.addWidget(self.chart_placeholder)
        
        self.main_layout.addWidget(self.chart_container, stretch=1)
        
        self.setLayout(self.main_layout)

