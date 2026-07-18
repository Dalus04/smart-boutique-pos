from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QFrame, QStyledItemDelegate, QProgressBar,
                               QPushButton, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

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
        self.setStyleSheet("background-color: #121212; color: #ffffff;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        title = QLabel("Inventario Inteligente")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        main_layout.addWidget(title)
        
        # Panel de KPIs
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)
        
        def crear_kpi(titulo, color_borde):
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #1e1e1e;
                    border-radius: 8px;
                    border-left: 4px solid {color_borde};
                    padding: 10px;
                }}
            """)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(15, 10, 15, 10)
            
            lbl_valor = QLabel("0")
            lbl_valor.setStyleSheet("color: #ffffff; font-size: 28px; font-weight: bold;")
            
            lbl_titulo = QLabel(titulo)
            lbl_titulo.setStyleSheet("color: #a0a0a0; font-size: 14px; font-weight: bold;")
            
            # Jerarquía invertida: Valor grande arriba, Título descriptivo abajo
            layout.addWidget(lbl_valor)
            layout.addWidget(lbl_titulo)
            return frame, lbl_valor
            
        self.kpi_frame_total, self.lbl_kpi_total = crear_kpi("Total de Productos", "#2a82da")
        self.kpi_frame_saludable, self.lbl_kpi_saludable = crear_kpi("Stock Saludable", "#2e7d32")
        self.kpi_frame_urgente, self.lbl_kpi_urgente = crear_kpi("Reposición Urgente", "#3d3d3d")
        
        kpi_layout.addWidget(self.kpi_frame_total)
        kpi_layout.addWidget(self.kpi_frame_saludable)
        kpi_layout.addWidget(self.kpi_frame_urgente)
        main_layout.addLayout(kpi_layout)
        
        # Panel de Filtros
        filters_frame = QFrame()
        filters_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
                min-width: 150px;
                color: #ffffff;
            }
            QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #ffffff;
                selection-background-color: #2a82da;
                selection-color: #ffffff;
            }
        """)
        filters_layout = QHBoxLayout(filters_frame)
        
        # Buscador Polimórfico
        filters_layout.addWidget(QLabel("Buscar Producto:"))
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Código o nombre del producto...")
        filters_layout.addWidget(self.txt_buscar)
        
        filters_layout.addWidget(QLabel("Categoría:"))
        self.combo_categoria = QComboBox()
        self.combo_categoria.addItem("Todas")
        filters_layout.addWidget(self.combo_categoria)
        
        filters_layout.addWidget(QLabel("Alerta Stock:"))
        self.combo_alerta = QComboBox()
        self.combo_alerta.addItems(["Todas", "Riesgo Alto", "Riesgo Medio", "Sin Riesgo"])
        filters_layout.addWidget(self.combo_alerta)
        
        filters_layout.addWidget(QLabel("Días de Espera de Proveedor:"))
        self.spin_dias_entrega = QSpinBox()
        self.spin_dias_entrega.setRange(1, 90)
        self.spin_dias_entrega.setValue(7)
        self.spin_dias_entrega.setToolTip("Define el tiempo estimado en días que tarda el proveedor en entregar un nuevo pedido para calcular la proyección de demanda y clasificar el riesgo de quiebre.")
        filters_layout.addWidget(self.spin_dias_entrega)
        
        filters_layout.addStretch()
        
        # Botones de Acción
        self.btn_actualizar = QPushButton(" Actualizar")
        self.btn_actualizar.setStyleSheet("""
            QPushButton {
                background-color: #2a82da; color: #ffffff;
                border-radius: 4px; padding: 6px 15px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #3b93eb; }
        """)
        
        self.btn_limpiar = QPushButton(" Limpiar Filtros")
        self.btn_limpiar.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d; color: #ffffff;
                border-radius: 4px; padding: 6px 15px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        
        self.btn_exportar = QPushButton(" Exportar CSV")
        self.btn_exportar.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32; color: #ffffff;
                border-radius: 4px; padding: 6px 15px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #3e8d42; }
        """)
        
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
        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(["Código", "Categoría", "Producto", "Stock Actual", "Venta Diaria Promedio", "Riesgo de Quiebre"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252525;
                gridline-color: #333333;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #333333;
                font-weight: bold;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }
        """)
        
        self.riesgo_delegate = RiesgoDelegate()
        self.tabla.setItemDelegateForColumn(5, self.riesgo_delegate)
        
        self.tabla.setSortingEnabled(True)
        main_layout.addWidget(self.tabla)
