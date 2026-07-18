from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QFrame, QStyledItemDelegate, QProgressBar,
                               QPushButton, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont
from utils.ui_helpers import crear_tabla_estandar, crear_tarjeta_kpi, crear_input_estandar, crear_combo_estandar, crear_boton, aplicar_estilo_panel, get_palette

class RiesgoDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        texto = index.data()
        if not texto:
            return
            
        rect = option.rect
        color = None
        text_color = QColor("#ffffff")
        if "Reposición urgente" in texto:
            color = QColor("#c62828") # Rojo
        elif "Alerta temprana" in texto:
            color = QColor("#f57c00") # Naranja
        elif "Stock saludable" in texto:
            color = QColor("#2e7d32") # Verde
            
        if color:
            painter.save()
            margin = 4
            bg_rect = rect.adjusted(margin, margin, -margin, -margin)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(bg_rect, 4, 4)
            
            painter.setPen(text_color)
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, texto)
            
            painter.restore()

class InventarioView(QWidget):
    def __init__(self):
        super().__init__()
        # Dejar heredar estilos de la ventana principal
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        title = QLabel("Inventario Inteligente")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)
        
        # Panel de KPIs
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)
        
        self.kpi_frame_total, self.lbl_kpi_total = crear_tarjeta_kpi("Total de Productos", color_borde="#2a82da")
        self.kpi_frame_saludable, self.lbl_kpi_saludable = crear_tarjeta_kpi("Stock Saludable", color_borde="#2e7d32")
        self.kpi_frame_urgente, self.lbl_kpi_urgente = crear_tarjeta_kpi("Reposición Urgente", color_borde="#3d3d3d")
        
        kpi_layout.addWidget(self.kpi_frame_total)
        kpi_layout.addWidget(self.kpi_frame_saludable)
        kpi_layout.addWidget(self.kpi_frame_urgente)
        main_layout.addLayout(kpi_layout)
        
        # Panel de Filtros
        filters_frame = QFrame()
        filters_frame.setProperty("factory_type", "panel")
        aplicar_estilo_panel(filters_frame, get_palette())
        filters_layout = QHBoxLayout(filters_frame)
        
        # Buscador Polimórfico
        filters_layout.addWidget(QLabel("Buscar Producto:"))
        self.txt_buscar = crear_input_estandar("Código o nombre del producto...")
        self.txt_buscar.setMinimumWidth(150)
        filters_layout.addWidget(self.txt_buscar)
        
        filters_layout.addWidget(QLabel("Categoría:"))
        self.combo_categoria = crear_combo_estandar(["Todas"])
        self.combo_categoria.setMinimumWidth(150)
        filters_layout.addWidget(self.combo_categoria)
        
        filters_layout.addWidget(QLabel("Alerta Stock:"))
        self.combo_alerta = crear_combo_estandar(["Todas", "Riesgo Alto", "Riesgo Medio", "Sin Riesgo"])
        self.combo_alerta.setMinimumWidth(150)
        filters_layout.addWidget(self.combo_alerta)
        
        filters_layout.addWidget(QLabel("Días de Espera de Proveedor:"))
        self.spin_dias_entrega = QSpinBox()
        self.spin_dias_entrega.setRange(1, 90)
        self.spin_dias_entrega.setValue(7)
        self.spin_dias_entrega.setToolTip("Define el tiempo estimado en días que tarda el proveedor en entregar un nuevo pedido para calcular la proyección de demanda y clasificar el riesgo de quiebre.")
        filters_layout.addWidget(self.spin_dias_entrega)
        
        filters_layout.addStretch()
        
        # Botones de Acción
        self.btn_actualizar = crear_boton(" Actualizar", tipo="primario")
        self.btn_limpiar = crear_boton(" Limpiar Filtros", tipo="secundario")
        self.btn_exportar = crear_boton(" Exportar CSV", tipo="exito")
        
        filters_layout.addWidget(self.btn_actualizar)
        filters_layout.addWidget(self.btn_limpiar)
        filters_layout.addWidget(self.btn_exportar)
        
        main_layout.addWidget(filters_frame)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e1e;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
        """)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        # Tabla de Inventario
        columnas = ["Código", "Categoría", "Producto", "Stock Actual", "Venta Diaria Promedio", "Última Actualización", "Riesgo de Quiebre"]
        self.tabla = crear_tabla_estandar(columnas, editable=False, row_height=35)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        
        self.riesgo_delegate = RiesgoDelegate()
        self.tabla.setItemDelegateForColumn(6, self.riesgo_delegate)
        
        self.tabla.setSortingEnabled(True)
        main_layout.addWidget(self.tabla)
