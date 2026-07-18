from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSpinBox, QDoubleSpinBox, QCompleter, QFrame)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from utils.ui_helpers import crear_tabla_estandar, crear_input_estandar, crear_combo_estandar, crear_boton, aplicar_estilo_panel, get_palette

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
        panel_superior.setProperty("factory_type", "panel")
        aplicar_estilo_panel(panel_superior, get_palette())
        panel_layout = QHBoxLayout(panel_superior)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        
        # Tarjeta Proveedor
        prov_layout = QVBoxLayout()
        lbl_prov_titulo = QLabel("Proveedor:")
        lbl_prov_titulo.setStyleSheet("font-size: 12px; font-weight: bold;")
        lbl_prov_titulo.setProperty("theme_color", "secondary")
        self.combo_proveedor = crear_combo_estandar()
        self.combo_proveedor.setEditable(True)
        self.combo_proveedor.setPlaceholderText("Seleccione un Proveedor...")
        self.combo_proveedor.setMinimumWidth(250)
        prov_layout.addWidget(lbl_prov_titulo)
        prov_layout.addWidget(self.combo_proveedor)
        panel_layout.addLayout(prov_layout)

        # Tarjeta Fecha
        fecha_layout = QVBoxLayout()
        lbl_fecha_titulo = QLabel("Fecha:")
        lbl_fecha_titulo.setStyleSheet("font-size: 12px; font-weight: bold;")
        lbl_fecha_titulo.setProperty("theme_color", "secondary")
        self.date_fecha = QDateEdit()
        self.date_fecha.setDate(QDate.currentDate())
        self.date_fecha.setCalendarPopup(True)
        fecha_layout.addWidget(lbl_fecha_titulo)
        fecha_layout.addWidget(self.date_fecha)
        panel_layout.addLayout(fecha_layout)

        # Tarjeta Documento / Factura
        doc_layout = QVBoxLayout()
        lbl_doc_titulo = QLabel("Factura/Serie:")
        lbl_doc_titulo.setStyleSheet("font-size: 12px; font-weight: bold;")
        lbl_doc_titulo.setProperty("theme_color", "secondary")
        self.line_factura = crear_input_estandar("Ej. F001-0001 (Opcional)")
        doc_layout.addWidget(lbl_doc_titulo)
        doc_layout.addWidget(self.line_factura)
        panel_layout.addLayout(doc_layout)
        
        panel_layout.addStretch()
        main_layout.addWidget(panel_superior)

        # --- PANEL DE BÚSQUEDA POLIMÓRFICA ---
        search_layout = QHBoxLayout()
        self.line_buscar = crear_input_estandar("Buscar Código o Nombre (Presione Enter para agregar)...")
        self.line_buscar.setMinimumHeight(40)
        font_buscar = QFont()
        font_buscar.setPointSize(12)
        self.line_buscar.setFont(font_buscar)
        search_layout.addWidget(self.line_buscar)
        main_layout.addLayout(search_layout)

        # --- GRILLA DE DETALLE ---
        columnas = ["Código", "Producto", "Stock Actual", "Cantidad", "Costo Unit.", "Subtotal", "Acciones"]
        self.tabla_detalle = crear_tabla_estandar(columnas, editable=False, alt_row_colors=True, row_height=35)
        header = self.tabla_detalle.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch) # El nombre ocupa el resto
        main_layout.addWidget(self.tabla_detalle)

        # --- PANEL INFERIOR: Checkout (Jerarquía Visual) ---
        checkout_frame = QFrame()
        checkout_frame.setProperty("factory_type", "panel")
        checkout_frame.setProperty("panel_tipo", "green")
        aplicar_estilo_panel(checkout_frame, get_palette())
        checkout_layout = QHBoxLayout(checkout_frame)
        checkout_layout.setContentsMargins(15, 10, 15, 10)
        
        self.btn_limpiar = crear_boton("Limpiar / Cancelar", tipo="secundario")
        
        checkout_layout.addWidget(self.btn_limpiar)
        checkout_layout.addStretch()
        
        self.lbl_total = QLabel("Total: $0.00")
        font_total = QFont()
        font_total.setPointSize(22)
        font_total.setBold(True)
        self.lbl_total.setFont(font_total)
        self.lbl_total.setStyleSheet("color: #4CAF50; background: transparent; border: none;")
        
        self.btn_emitir = crear_boton("EMITIR COMPRA", tipo="exito")
        
        checkout_layout.addWidget(self.lbl_total)
        checkout_layout.addSpacing(20)
        checkout_layout.addWidget(self.btn_emitir)
        
        main_layout.addWidget(checkout_frame)
