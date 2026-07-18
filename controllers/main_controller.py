from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from views.main_window import MainWindow
from controllers.dashboard_controller import DashboardController
from controllers.pos_controller import POSController

class MainController:
    def __init__(self):
        self.window = MainWindow()

        # Instanciar los controladores secundarios
        self.dashboard_controller = DashboardController()
        self.pos_controller = POSController()
        
        # Placeholders para otros módulos (ej. Inventario)
        self.inventario_view = QWidget()
        inv_layout = QVBoxLayout(self.inventario_view)
        inv_label = QLabel("Módulo de Inventario - En construcción")
        inv_label.setStyleSheet("font-size: 20px; color: #888888;")
        inv_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inv_layout.addWidget(inv_label)

        # Agregar las vistas al QStackedWidget de MainWindow
        self.window.stack.addWidget(self.dashboard_controller.view)
        self.window.stack.addWidget(self.pos_controller.view)
        self.window.stack.addWidget(self.inventario_view)

        # Conectar las señales de los botones a la lógica de navegación
        self.window.btn_dashboard.clicked.connect(self.show_dashboard)
        self.window.btn_pos.clicked.connect(self.show_pos)
        self.window.btn_inventario.clicked.connect(self.show_inventario)

    def show_dashboard(self):
        self.window.stack.setCurrentWidget(self.dashboard_controller.view)
        self.window.set_active_button(self.window.btn_dashboard)
        self.dashboard_controller.start()

    def show_pos(self):
        self.window.stack.setCurrentWidget(self.pos_controller.view)
        self.window.set_active_button(self.window.btn_pos)
        self.pos_controller.view.txt_codigo.setFocus()

    def show_inventario(self):
        self.window.stack.setCurrentWidget(self.inventario_view)
        self.window.set_active_button(self.window.btn_inventario)

    def start(self):
        # Al arrancar, mostrar el dashboard y comenzar a cargar datos
        self.dashboard_controller.start()
        self.window.showMaximized()
