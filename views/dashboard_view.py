from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QProgressBar, QFrame, QButtonGroup, QPushButton, 
                                 QStackedWidget, QScrollArea)
from PySide6.QtCore import Qt
from utils.ui_helpers import get_palette

class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        
        # Izquierda: Main Content (Operativo y Comercial)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(20)
        
        # === BLOQUE 1: ESTADO OPERATIVO ===
        self.header_layout = QHBoxLayout()
        self.title_label = QLabel("Centro de Inteligencia Comercial")
        self.title_label.setStyleSheet("font-size: 26px; font-weight: bold;")
        
        # Filtros: Button Group
        self.filter_layout = QHBoxLayout()
        self.filter_layout.setSpacing(0)
        self.btn_group_periodo = QButtonGroup(self)
        self.btn_group_periodo.setExclusive(True)
        
        btn_hoy = self._crear_btn_filtro("Hoy")
        btn_semana = self._crear_btn_filtro("Semana")
        btn_mes = self._crear_btn_filtro("Mes")
        btn_anio = self._crear_btn_filtro("Año")
        
        btn_semana.setChecked(True)
        
        self.btn_group_periodo.addButton(btn_hoy, 1)
        self.btn_group_periodo.addButton(btn_semana, 2)
        self.btn_group_periodo.addButton(btn_mes, 3)
        self.btn_group_periodo.addButton(btn_anio, 4)
        
        self.filter_layout.addWidget(btn_hoy)
        self.filter_layout.addWidget(btn_semana)
        self.filter_layout.addWidget(btn_mes)
        self.filter_layout.addWidget(btn_anio)
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addLayout(self.filter_layout)
        
        self.left_layout.addLayout(self.header_layout)
        
        # Salud del Negocio (Protagonista)
        self.card_salud = QFrame()
        paleta = get_palette()
        self.card_salud.setStyleSheet(f"""
            QFrame {{
                background-color: {paleta['bg_element']};
                border-radius: 8px;
                border: 1px solid {paleta['border']};
            }}
        """)
        self.health_layout = QHBoxLayout(self.card_salud)
        self.health_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_h_title = QLabel("Salud del Negocio:")
        lbl_h_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {paleta['text_primary']}; border: none;")
        
        self.lbl_h_info = QLabel("ℹ️")
        self.lbl_h_info.setStyleSheet("font-size: 14px; border: none; background: transparent;")
        self.lbl_h_info.setToolTip("<html><body><b>Score de Salud (0-100):</b><ul><li>+30 si hay Utilidad Positiva</li><li>+30 si las Ventas crecen</li><li>+40 si no hay stock Crítico</li></ul></body></html>")
        
        self.lbl_h_estado = QLabel("Analizando...")
        self.lbl_h_estado.setStyleSheet("font-size: 16px; font-weight: bold; color: #a0a0a0; border: none;")
        
        self.progress_health = QProgressBar()
        self.progress_health.setFixedHeight(18)
        self.progress_health.setTextVisible(False)
        self.progress_health.setRange(0, 100)
        self.progress_health.setValue(0)
        self.progress_health.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 9px;
                background-color: #333333;
            }
            QProgressBar::chunk {
                border-radius: 9px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e74c3c, stop:0.5 #f39c12, stop:1 #27ae60);
            }
        """)
        self.lbl_health_score = QLabel("0/100")
        self.lbl_health_score.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {paleta['text_primary']}; border: none;")
        
        self.health_layout.addWidget(lbl_h_title)
        self.health_layout.addWidget(self.lbl_h_info)
        self.health_layout.addWidget(self.lbl_h_estado)
        self.health_layout.addSpacing(20)
        self.health_layout.addWidget(self.progress_health, stretch=1)
        self.health_layout.addWidget(self.lbl_health_score)
        
        self.left_layout.addWidget(self.card_salud)
        
        # Tarjetas KPI
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(15)
        
        self.lbl_ventas_val, self.lbl_ventas_var = self._crear_kpi_card(self.kpi_layout, "Ventas", "#2a82da", "Azul", "Total recaudado en el periodo.")
        self.lbl_utilidad_val, self.lbl_utilidad_var = self._crear_kpi_card(self.kpi_layout, "Utilidad Bruta", "#27ae60", "Verde", "Diferencia entre Precio y Costo de lo vendido.")
        self.lbl_margen_val, self.lbl_margen_var = self._crear_kpi_card(self.kpi_layout, "Margen Bruto %", "#f39c12", "Naranja", "Porcentaje de utilidad sobre las ventas totales.")
        self.lbl_clientes_val, self.lbl_clientes_var = self._crear_kpi_card(self.kpi_layout, "Nuevos Clientes", "#8e44ad", "Morado", "Clientes únicos atendidos en el periodo.")
        
        self.lbl_proyeccion_val, self.progress_proyeccion = self._crear_kpi_proyeccion(self.kpi_layout)
        
        self.left_layout.addLayout(self.kpi_layout)
        
        # === BLOQUE 2: RENDIMIENTO COMERCIAL ===
        self.stacked_widget = QStackedWidget()
        
        # Index 0: Canvas Matplotlib
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_placeholder = QLabel("Cargando métricas y gráficos...")
        self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_layout.addWidget(self.chart_placeholder)
        
        self.stacked_widget.addWidget(self.chart_container)
        
        # Index 1: Fallback Resumen Ejecutivo
        self.fallback_container = QFrame()
        self.fallback_container.setStyleSheet(f"""
            QFrame {{
                background-color: {paleta['bg_element']};
                border: 1px dashed {paleta['border']};
                border-radius: 8px;
            }}
        """)
        self.fallback_layout = QVBoxLayout(self.fallback_container)
        self.fallback_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_fb_title = QLabel("Resumen Ejecutivo (Datos Insuficientes)")
        self.lbl_fb_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2a82da; border: none;")
        self.lbl_fb_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_fb_msg = QLabel("No hay historial temporal suficiente para generar gráficos de tendencia.")
        self.lbl_fb_msg.setStyleSheet(f"font-size: 15px; color: {paleta['text_primary']}; border: none;")
        self.lbl_fb_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fb_msg.setWordWrap(True)
        
        self.fallback_layout.addWidget(self.lbl_fb_title)
        self.fallback_layout.addWidget(self.lbl_fb_msg)
        
        self.stacked_widget.addWidget(self.fallback_container)
        
        self.left_layout.addWidget(self.stacked_widget, stretch=1)
        
        self.main_layout.addWidget(self.left_panel, stretch=7)
        
        # === BLOQUE 3: INTELIGENCIA COMERCIAL ===
        self.right_panel = QFrame()
        self.right_panel.setFixedWidth(350)
        self.right_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {paleta['bg_alt']};
                border: 1px solid {paleta['border']};
                border-radius: 8px;
            }}
        """)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_ia_title = QLabel("🤖 Insights Activos")
        self.lbl_ia_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none; background: transparent;")
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        
        self.right_layout.addWidget(self.lbl_ia_title)
        self.right_layout.addWidget(self.scroll_area)
        
        self.main_layout.addWidget(self.right_panel)

    def _crear_btn_filtro(self, texto):
        paleta = get_palette()
        btn = QPushButton(texto)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {paleta['bg_element']};
                color: {paleta['text_primary']};
                border: 1px solid {paleta['border']};
                padding: 6px 16px;
                font-weight: bold;
                border-radius: 4px;
                margin: 0px 2px;
            }}
            QPushButton:checked {{
                background-color: #2a82da;
                color: #ffffff;
                border: 1px solid #2a82da;
            }}
            QPushButton:hover:!checked {{
                background-color: {paleta['hover']};
            }}
        """)
        return btn

    def _crear_kpi_card(self, parent_layout, titulo, border_color, title_color_name, tooltip):
        frame = QFrame()
        paleta = get_palette()
        
        color_map = {
            "Azul": "#2a82da",
            "Verde": "#27ae60",
            "Naranja": "#f39c12",
            "Morado": "#8e44ad"
        }
        title_color = color_map.get(title_color_name, paleta['text_secondary'])
        
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {paleta['bg_element']};
                border-radius: 8px;
                border-bottom: 4px solid {border_color};
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_tit = QLabel(titulo)
        lbl_tit.setStyleSheet(f"color: {title_color}; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        
        lbl_val = QLabel("0")
        lbl_val.setStyleSheet(f"color: {paleta['text_primary']}; font-size: 26px; font-weight: bold; border: none; background: transparent;")
        lbl_val.setToolTip(f"<html><body>{tooltip}</body></html>")
        
        lbl_var = QLabel("0%")
        lbl_var.setStyleSheet(f"color: #a0a0a0; font-size: 12px; border: none; background: transparent;")
        
        layout.addWidget(lbl_tit)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_var)
        
        parent_layout.addWidget(frame)
        return lbl_val, lbl_var

    def _crear_kpi_proyeccion(self, parent_layout):
        frame = QFrame()
        paleta = get_palette()
        
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {paleta['bg_element']};
                border-radius: 8px;
                border-bottom: 4px solid #16a085;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_tit = QLabel("Proyección Mensual")
        lbl_tit.setStyleSheet(f"color: #16a085; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        
        lbl_val = QLabel("$0.00")
        lbl_val.setStyleSheet(f"color: {paleta['text_primary']}; font-size: 20px; font-weight: bold; border: none; background: transparent;")
        lbl_val.setToolTip("<html><body>Cálculo lineal de ventas proyectadas a fin de mes.</body></html>")
        
        progress = QProgressBar()
        progress.setFixedHeight(4)
        progress.setTextVisible(False)
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setStyleSheet("""
            QProgressBar { border: none; background-color: #333333; }
            QProgressBar::chunk { background-color: #16a085; }
        """)
        
        layout.addWidget(lbl_tit)
        layout.addWidget(lbl_val)
        layout.addWidget(progress)
        
        parent_layout.addWidget(frame)
        return lbl_val, progress
