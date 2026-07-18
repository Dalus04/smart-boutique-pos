from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSpinBox, QDoubleSpinBox, QCompleter, QFrame
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

class ComprasView(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- PANEL SUPERIOR: Tarjetas de Resumen (Metadatos) ---
        panel_superior = QFrame()
        panel_superior.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        panel_layout = QHBoxLayout(panel_superior)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        
        # Tarjeta Proveedor
        prov_layout = QVBoxLayout()
        lbl_prov_titulo = QLabel("Proveedor:")
        lbl_prov_titulo.setStyleSheet("font-size: 12px; font-weight: bold; color: #BDBDBD;")
        self.combo_proveedor = QComboBox()
        self.combo_proveedor.setEditable(True)
        self.combo_proveedor.setPlaceholderText("Seleccione un Proveedor...")
        self.combo_proveedor.setMinimumWidth(250)
        prov_layout.addWidget(lbl_prov_titulo)
        prov_layout.addWidget(self.combo_proveedor)
        panel_layout.addLayout(prov_layout)

        # Tarjeta Fecha
        fecha_layout = QVBoxLayout()
        lbl_fecha_titulo = QLabel("Fecha:")
        lbl_fecha_titulo.setStyleSheet("font-size: 12px; font-weight: bold; color: #BDBDBD;")
        self.date_fecha = QDateEdit()
        self.date_fecha.setDate(QDate.currentDate())
        self.date_fecha.setCalendarPopup(True)
        fecha_layout.addWidget(lbl_fecha_titulo)
        fecha_layout.addWidget(self.date_fecha)
        panel_layout.addLayout(fecha_layout)

        # Tarjeta Documento / Factura
        doc_layout = QVBoxLayout()
        lbl_doc_titulo = QLabel("Factura/Serie:")
        lbl_doc_titulo.setStyleSheet("font-size: 12px; font-weight: bold; color: #BDBDBD;")
        self.line_factura = QLineEdit()
        self.line_factura.setPlaceholderText("Ej. F001-0001 (Opcional)")
        doc_layout.addWidget(lbl_doc_titulo)
        doc_layout.addWidget(self.line_factura)
        panel_layout.addLayout(doc_layout)
        
        panel_layout.addStretch()
        main_layout.addWidget(panel_superior)

        # --- PANEL DE BÚSQUEDA POLIMÓRFICA ---
        search_layout = QHBoxLayout()
        self.line_buscar = QLineEdit()
        self.line_buscar.setPlaceholderText("Buscar Código o Nombre (Presione Enter para agregar)...")
        self.line_buscar.setMinimumHeight(40)
        font_buscar = QFont()
        font_buscar.setPointSize(12)
        self.line_buscar.setFont(font_buscar)
        search_layout.addWidget(self.line_buscar)
        main_layout.addLayout(search_layout)

        # --- GRILLA DE DETALLE ---
        self.tabla_detalle = QTableWidget(0, 7)
        self.tabla_detalle.setHorizontalHeaderLabels([
            "Código", "Producto", "Stock Actual", "Cantidad", "Costo Unit.", "Subtotal", "Acciones"
        ])
        header = self.tabla_detalle.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch) # El nombre ocupa el resto
        main_layout.addWidget(self.tabla_detalle)

        # --- PANEL INFERIOR: Checkout (Jerarquía Visual) ---
        checkout_frame = QFrame()
        checkout_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(76, 175, 80, 0.05);
                border-radius: 8px;
                border: 1px solid rgba(76, 175, 80, 0.2);
            }
        """)
        checkout_layout = QHBoxLayout(checkout_frame)
        checkout_layout.setContentsMargins(15, 10, 15, 10)
        
        self.btn_limpiar = QPushButton("Limpiar / Cancelar")
        self.btn_limpiar.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); padding: 10px; border-radius: 4px; font-weight: bold;")
        
        checkout_layout.addWidget(self.btn_limpiar)
        checkout_layout.addStretch()
        
        self.lbl_total = QLabel("Total: $0.00")
        font_total = QFont()
        font_total.setPointSize(22)
        font_total.setBold(True)
        self.lbl_total.setFont(font_total)
        self.lbl_total.setStyleSheet("color: #4CAF50; background: transparent; border: none;")
        
        self.btn_emitir = QPushButton("EMITIR COMPRA")
        self.btn_emitir.setStyleSheet("background-color: #388E3C; color: white; padding: 15px 30px; font-weight: bold; font-size: 16px; border-radius: 6px;")
        
        checkout_layout.addWidget(self.lbl_total)
        checkout_layout.addSpacing(20)
        checkout_layout.addWidget(self.btn_emitir)
        
        main_layout.addWidget(checkout_frame)
