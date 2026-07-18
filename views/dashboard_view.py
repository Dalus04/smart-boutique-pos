from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from PySide6.QtCore import Qt

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
        self.lbl_salud_inv = self._create_kpi_card("Items Críticos (Inventario)")
        self.lbl_unidades_inv = self._create_kpi_card("Unidades (Óptimo)")
        self.lbl_total_ventas = self._create_kpi_card("Total Transacciones")
        
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

    def _create_kpi_card(self, title: str) -> QLabel:
        card = QGroupBox()
        card.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #b0b0b0; font-size: 14px;")
        
        value_label = QLabel("Cargando...")
        value_label.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        self.kpi_layout.addWidget(card)
        
        return value_label
