from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QComboBox, QLabel, QGroupBox, QFrame, QSpinBox, QCompleter, QLineEdit
from PySide6.QtCore import Qt
from utils.ui_helpers import crear_tabla_estandar, crear_boton, crear_combo_estandar, crear_input_estandar

class QuantityWidget(QWidget):
    def __init__(self, quantity, on_increment, on_decrement, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Alinear a la derecha agregando un stretch al principio
        layout.addStretch()
        
        self.btn_minus = QPushButton("-")
        self.btn_minus.setFixedWidth(24)
        self.btn_minus.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.btn_minus.clicked.connect(on_decrement)
        
        self.lbl_qty = QLabel(str(quantity))
        self.lbl_qty.setFixedWidth(30)
        self.lbl_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qty.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedWidth(24)
        self.btn_plus.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
        self.btn_plus.clicked.connect(on_increment)
        
        layout.addWidget(self.btn_minus)
        layout.addWidget(self.lbl_qty)
        layout.addWidget(self.btn_plus)


class POSView(QWidget):
    def __init__(self):
        super().__init__()
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # --- PANEL IZQUIERDO: Carrito y Búsqueda ---
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Sección de selección rápida y adición en dos filas
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)
        
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)
        
        # Combo Categoría
        cat_label = QLabel("Categoría:")
        cat_label.setStyleSheet("font-size: 15px; color: #ffffff;")
        self.combo_categorias = crear_combo_estandar(["Todas"])
        self.combo_categorias.setMinimumWidth(120)
        
        # Entrada de Código (con Placeholder largo e interactividad de Foco)
        cod_label = QLabel("Código:")
        cod_label.setStyleSheet("font-size: 15px; color: #ffffff;")
        self.txt_codigo = crear_input_estandar("Ingrese un código...")
        self.txt_codigo.setFixedWidth(130) # Un poco más ancho para albergar el placeholder
        
        search_label = QLabel("Producto:")
        search_label.setStyleSheet("font-size: 15px; color: #ffffff;")
        
        self.combo_productos = crear_combo_estandar()
        self.combo_productos.setMinimumWidth(200)
        self.combo_productos.setEditable(True)
        self.combo_productos.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_productos.setPlaceholderText("Seleccione un producto...")
        
        # Configurar QCompleter para autocompletado en caliente
        self.completer = QCompleter(self.combo_productos.model(), self)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # Estilo del pop-up del QCompleter
        popup = self.completer.popup()
        popup.setStyleSheet("""
            QListView {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                selection-background-color: #2a82da;
                selection-color: #ffffff;
            }
            QListView::item {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QListView::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }
        """)
        self.combo_productos.setCompleter(self.completer)

        # Etiqueta de Stock Dinámica
        self.lbl_stock = QLabel("Stock: --")
        self.lbl_stock.setStyleSheet("font-size: 16px; color: #a0a0a0; font-weight: bold; margin-left: 5px;")

        # Label y selector de cantidad (QSpinBox con botones + y - manuales a los lados)
        qty_label = QLabel("Cant:")
        qty_label.setStyleSheet("font-size: 14px; color: #ffffff; margin-left: 5px;")
        
        self.btn_minus_qty = crear_boton("-", tipo="secundario")
        self.btn_minus_qty.setFixedWidth(30)
        
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setRange(1, 999)
        self.spin_cantidad.setValue(1)
        self.spin_cantidad.setFixedWidth(50)
        self.spin_cantidad.setStyleSheet("""
            QSpinBox {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 5px;
            }
            QSpinBox:focus {
                border: 1px solid #2a82da;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px; /* Ocultar flechas nativas para priorizar botones +/- laterales */
            }
        """)
        
        self.btn_plus_qty = crear_boton("+", tipo="secundario")
        self.btn_plus_qty.setFixedWidth(30)
        
        # Conexión básica de incremento/decremento rápido
        self.btn_minus_qty.clicked.connect(lambda: self.spin_cantidad.setValue(max(1, self.spin_cantidad.value() - 1)))
        self.btn_plus_qty.clicked.connect(lambda: self.spin_cantidad.setValue(min(999, self.spin_cantidad.value() + 1)))
        
        self.btn_agregar = crear_boton("Agregar", tipo="primario")
        self.btn_agregar.setEnabled(False) # Deshabilitado inicialmente

        # Botón Limpiar Búsqueda ("Limpiar selección")
        self.btn_limpiar_busqueda = crear_boton("Limpiar selección", tipo="secundario")

        # Etiqueta de confirmación visual breve
        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setStyleSheet("font-size: 13px; font-weight: bold; color: #5cb85c; margin-left: 5px;")
        
        row1_layout.addWidget(cat_label)
        row1_layout.addWidget(self.combo_categorias)
        row1_layout.addWidget(cod_label)
        row1_layout.addWidget(self.txt_codigo)
        row1_layout.addWidget(search_label)
        row1_layout.addWidget(self.combo_productos, stretch=1)
        
        row2_layout.addWidget(self.lbl_stock)
        row2_layout.addWidget(qty_label)
        row2_layout.addWidget(self.btn_minus_qty)
        row2_layout.addWidget(self.spin_cantidad)
        row2_layout.addWidget(self.btn_plus_qty)
        row2_layout.addWidget(self.btn_agregar)
        row2_layout.addWidget(self.btn_limpiar_busqueda)
        row2_layout.addStretch()
        
        left_layout.addLayout(row1_layout)
        left_layout.addLayout(row2_layout)
        
        # Tabla del carrito
        columnas = ["Código", "Producto", "Cantidad", "Precio", "Subtotal", "Acción"]
        self.cart_table = crear_tabla_estandar(columnas, editable=False, alt_row_colors=True, row_height=40)
        
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.cart_table.setColumnWidth(0, 70)
        self.cart_table.setColumnWidth(2, 110) # Mayor espacio para controles +/-
        self.cart_table.setColumnWidth(3, 100)
        self.cart_table.setColumnWidth(4, 100)
        self.cart_table.setColumnWidth(5, 70)
        
        left_layout.addWidget(self.cart_table)
        
        self.btn_limpiar = crear_boton("Limpiar Carrito", tipo="peligro")
        left_layout.addWidget(self.btn_limpiar, alignment=Qt.AlignmentFlag.AlignRight)
        
        # --- PANEL DERECHO: Resumen, Sugerencias y Checkout ---
        right_panel = QFrame()
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # Grupo: Resumen de Venta
        summary_group = QGroupBox("Resumen de Venta")
        summary_group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
                font-weight: bold;
                color: #ffffff;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        summary_layout = QVBoxLayout(summary_group)
        
        total_label = QLabel("Total:")
        total_label.setStyleSheet("color: #b0b0b0; font-size: 18px;")
        self.lbl_total = QLabel("$ 0.00")
        self.lbl_total.setStyleSheet("color: #ffffff; font-size: 48px; font-weight: bold;") # Mayor tamaño/protagonismo del total
        
        summary_layout.addWidget(total_label)
        summary_layout.addWidget(self.lbl_total)
        
        right_layout.addWidget(summary_group)
        
        # Grupo: Sugerencias Inteligentes (Venta Cruzada con Acento Visual Azul/Dorado)
        self.suggestions_group = QGroupBox("Recomendación Inteligente")
        self.suggestions_group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e1e;
                border: 2px solid #2a82da;
                border-radius: 8px;
                font-weight: bold;
                color: #2a82da;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        self.suggestions_layout = QVBoxLayout(self.suggestions_group)
        self.suggestions_layout.setSpacing(10)
        
        self.lbl_sug_subtitle = QLabel("Basada en patrones de compra")
        self.lbl_sug_subtitle.setStyleSheet("color: #a0a0a0; font-size: 12px; font-weight: normal; margin-bottom: 5px;")
        self.suggestions_layout.addWidget(self.lbl_sug_subtitle)
        
        self.lbl_no_suggestions = QLabel("Agrega productos al carrito para ver recomendaciones de IA.")
        self.lbl_no_suggestions.setStyleSheet("color: #a0a0a0; font-style: italic; font-size: 12px;")
        self.lbl_no_suggestions.setWordWrap(True)
        self.suggestions_layout.addWidget(self.lbl_no_suggestions)
        
        right_layout.addWidget(self.suggestions_group, stretch=1)
        
        # Grupo: Checkout (Con mayor espaciado vertical)
        checkout_group = QGroupBox("Checkout")
        checkout_group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
                font-weight: bold;
                color: #ffffff;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        checkout_layout = QVBoxLayout(checkout_group)
        checkout_layout.setSpacing(20) # Mayor espaciado vertical entre controles de Cliente y Medio de Pago
        
        lbl_cliente = QLabel("Cliente:")
        lbl_cliente.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        
        # Combo Cliente (editable y autocompletable con Placeholder e interactividad de Foco)
        self.combo_cliente = crear_combo_estandar(["Consumidor Final"])
        self.combo_cliente.setEditable(True)
        self.combo_cliente.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_cliente.setPlaceholderText("Buscar cliente...")
        
        self.cliente_completer = QCompleter(self.combo_cliente.model(), self)
        self.cliente_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.cliente_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        popup_cli = self.cliente_completer.popup()
        popup_cli.setStyleSheet("""
            QListView {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                selection-background-color: #2a82da;
                selection-color: #ffffff;
            }
            QListView::item {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QListView::item:selected {
                background-color: #2a82da;
                color: #ffffff;
            }
        """)
        self.combo_cliente.setCompleter(self.cliente_completer)

        # Botón para limpiar cliente
        self.btn_limpiar_cliente = crear_boton("Limpiar selección", tipo="secundario")

        # Layout horizontal para combo_cliente y su botón limpiar
        cliente_layout = QHBoxLayout()
        cliente_layout.setSpacing(8)
        cliente_layout.addWidget(self.combo_cliente, stretch=1)
        cliente_layout.addWidget(self.btn_limpiar_cliente)
        
        lbl_pago = QLabel("Medio de Pago:")
        lbl_pago.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        self.combo_pago = crear_combo_estandar()
        
        self.btn_procesar = crear_boton("Procesar Venta", tipo="exito")
        
        checkout_layout.addWidget(lbl_cliente)
        checkout_layout.addLayout(cliente_layout)
        checkout_layout.addWidget(lbl_pago)
        checkout_layout.addWidget(self.combo_pago)
        checkout_layout.addWidget(self.btn_procesar)
        
        right_layout.addWidget(checkout_group)
        
        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(right_panel)
        
        self.setLayout(main_layout)
