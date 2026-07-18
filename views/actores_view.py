from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QHeaderView, QFrame, QTabWidget)
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from utils.ui_helpers import crear_tabla_estandar, crear_input_estandar, crear_boton

class ActoresView(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #121212; color: #ffffff;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        title = QLabel("Clientes y Proveedores")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        main_layout.addWidget(title)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::panel {
                border: 1px solid #2d2d2d;
                background-color: #121212;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #1e1e1e;
                color: #b0b0b0;
                border: 1px solid #2d2d2d;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #2a82da;
                color: #ffffff;
                border: 1px solid #2a82da;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2d2d2d;
                color: #ffffff;
            }
        """)
        
        # Tab Clientes
        self.tab_clientes = QWidget()
        self._init_tab_clientes()
        self.tabs.addTab(self.tab_clientes, "Clientes")
        
        # Tab Proveedores
        self.tab_proveedores = QWidget()
        self._init_tab_proveedores()
        self.tabs.addTab(self.tab_proveedores, "Proveedores")
        
        main_layout.addWidget(self.tabs)
        
    def _init_tab_clientes(self):
        layout = QHBoxLayout(self.tab_clientes)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        # Form Panel (Left)
        form_frame = QFrame()
        form_frame.setFixedWidth(300)
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(12)
        
        self.lbl_titulo_form_cliente = QLabel("Nuevo Cliente")
        self.lbl_titulo_form_cliente.setStyleSheet("font-size: 18px; font-weight: bold; color: #2a82da; padding-bottom: 5px;")
        form_layout.addWidget(self.lbl_titulo_form_cliente)
        
        form_layout.addWidget(QLabel("DNI / Código (Requerido):"))
        self.txt_cliente_id = crear_input_estandar("Ej. 12345678")
        self.txt_cliente_id.setValidator(QRegularExpressionValidator(QRegularExpression("^\\d{1,12}$")))
        form_layout.addWidget(self.txt_cliente_id)
        
        form_layout.addWidget(QLabel("Nombres Completos (Requerido):"))
        self.txt_cliente_nombre = crear_input_estandar("Ej. Daniel Alfonzo")
        form_layout.addWidget(self.txt_cliente_nombre)
        
        form_layout.addWidget(QLabel("Teléfono:"))
        self.txt_cliente_telefono = crear_input_estandar("Ej. +51999888777")
        form_layout.addWidget(self.txt_cliente_telefono)
        
        form_layout.addWidget(QLabel("Correo Electrónico:"))
        self.txt_cliente_correo = crear_input_estandar("Ej. daniel@example.com")
        form_layout.addWidget(self.txt_cliente_correo)
        
        form_layout.addStretch()
        
        # Botones del formulario
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_guardar_cliente = crear_boton("Guardar", tipo="exito")
        self.btn_limpiar_cliente = crear_boton("Limpiar Formulario", tipo="secundario")
        
        btn_layout.addWidget(self.btn_guardar_cliente)
        btn_layout.addWidget(self.btn_limpiar_cliente)
        form_layout.addLayout(btn_layout)
        
        layout.addWidget(form_frame)
        
        # Table & Actions Panel (Right)
        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(12)
        
        # Buscador superior
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar:"))
        self.txt_buscar_cliente = crear_input_estandar("Código (DNI) o nombre del cliente...")
        search_layout.addWidget(self.txt_buscar_cliente)
        table_layout.addLayout(search_layout)
        
        columnas_clientes = ["Código (DNI)", "Nombres Completos", "Teléfono", "Correo Electrónico"]
        self.tabla_clientes = crear_tabla_estandar(columnas_clientes, editable=False, alt_row_colors=True, row_height=35)
        self.tabla_clientes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_clientes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_clientes.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_clientes.setSortingEnabled(True)
        table_layout.addWidget(self.tabla_clientes)
        
        # Botones inferiores de la tabla
        table_btn_layout = QHBoxLayout()
        table_btn_layout.addStretch()
        
        self.btn_editar_cliente = crear_boton("Editar Seleccionado", tipo="primario")
        self.btn_eliminar_cliente = crear_boton("Eliminar Seleccionado", tipo="peligro")
        
        table_btn_layout.addWidget(self.btn_editar_cliente)
        table_btn_layout.addWidget(self.btn_eliminar_cliente)
        table_layout.addLayout(table_btn_layout)
        
        layout.addWidget(table_panel)
        
    def _init_tab_proveedores(self):
        layout = QHBoxLayout(self.tab_proveedores)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        # Form Panel (Left)
        form_frame = QFrame()
        form_frame.setFixedWidth(300)
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(12)
        
        self.lbl_titulo_form_proveedor = QLabel("Nuevo Proveedor")
        self.lbl_titulo_form_proveedor.setStyleSheet("font-size: 18px; font-weight: bold; color: #2a82da; padding-bottom: 5px;")
        form_layout.addWidget(self.lbl_titulo_form_proveedor)
        
        form_layout.addWidget(QLabel("RUC / Código (Requerido):"))
        self.txt_proveedor_id = crear_input_estandar("Ej. 20123456789")
        self.txt_proveedor_id.setValidator(QRegularExpressionValidator(QRegularExpression("^\\d{1,8}$")))
        form_layout.addWidget(self.txt_proveedor_id)
        
        form_layout.addWidget(QLabel("Nombre o Razón Social (Requerido):"))
        self.txt_proveedor_nombre = crear_input_estandar("Ej. Textiles Del Sur S.A.C.")
        form_layout.addWidget(self.txt_proveedor_nombre)
        
        form_layout.addWidget(QLabel("Teléfono:"))
        self.txt_proveedor_telefono = crear_input_estandar("Ej. 01-4445555")
        form_layout.addWidget(self.txt_proveedor_telefono)
        
        form_layout.addWidget(QLabel("Dirección:"))
        self.txt_proveedor_direccion = crear_input_estandar("Ej. Av. Industrial 123, Lima")
        form_layout.addWidget(self.txt_proveedor_direccion)
        
        form_layout.addWidget(QLabel("Correo Electrónico:"))
        self.txt_proveedor_correo = crear_input_estandar("Ej. contacto@textilesdelsur.com")
        form_layout.addWidget(self.txt_proveedor_correo)
        
        form_layout.addStretch()
        
        # Botones del formulario
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_guardar_proveedor = crear_boton("Guardar", tipo="exito")
        self.btn_limpiar_proveedor = crear_boton("Limpiar Formulario", tipo="secundario")
        
        btn_layout.addWidget(self.btn_guardar_proveedor)
        btn_layout.addWidget(self.btn_limpiar_proveedor)
        form_layout.addLayout(btn_layout)
        
        layout.addWidget(form_frame)
        
        # Table & Actions Panel (Right)
        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(12)
        
        # Buscador superior
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar:"))
        self.txt_buscar_proveedor = crear_input_estandar("Código (RUC) o razón social...")
        search_layout.addWidget(self.txt_buscar_proveedor)
        table_layout.addLayout(search_layout)
        
        columnas_proveedores = ["Código (RUC)", "Nombre / Razón Social", "Teléfono", "Dirección", "Correo Electrónico"]
        self.tabla_proveedores = crear_tabla_estandar(columnas_proveedores, editable=False, alt_row_colors=True, row_height=35)
        self.tabla_proveedores.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_proveedores.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_proveedores.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_proveedores.setSortingEnabled(True)
        table_layout.addWidget(self.tabla_proveedores)
        
        # Botones inferiores de la tabla
        table_btn_layout = QHBoxLayout()
        table_btn_layout.addStretch()
        
        self.btn_editar_proveedor = crear_boton("Editar Seleccionado", tipo="primario")
        self.btn_eliminar_proveedor = crear_boton("Eliminar Seleccionado", tipo="peligro")
        
        table_btn_layout.addWidget(self.btn_editar_proveedor)
        table_btn_layout.addWidget(self.btn_eliminar_proveedor)
        table_layout.addLayout(table_btn_layout)
        
        layout.addWidget(table_panel)
