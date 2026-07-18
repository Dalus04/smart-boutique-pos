from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from views.main_window import MainWindow
from controllers.dashboard_controller import DashboardController
from controllers.pos_controller import POSController
from controllers.inventario_controller import InventarioController
from controllers.actores_controller import ActoresController

class MainController:
    def __init__(self):
        self.window = MainWindow()

        # Instanciar los controladores secundarios
        self.dashboard_controller = DashboardController()
        self.pos_controller = POSController()
        self.inventario_controller = InventarioController()
        self.actores_controller = ActoresController()

        # Agregar las vistas al QStackedWidget de MainWindow
        self.window.stack.addWidget(self.dashboard_controller.view)
        self.window.stack.addWidget(self.pos_controller.view)
        self.window.stack.addWidget(self.inventario_controller.view)
        self.window.stack.addWidget(self.actores_controller.view)

        # Conectar las señales de los botones a la lógica de navegación
        self.window.btn_dashboard.clicked.connect(self.show_dashboard)
        self.window.btn_pos.clicked.connect(self.show_pos)
        self.window.btn_inventario.clicked.connect(self.show_inventario)
        self.window.btn_actores.clicked.connect(self.show_actores)

    def show_dashboard(self):
        self.window.stack.setCurrentWidget(self.dashboard_controller.view)
        self.window.set_active_button(self.window.btn_dashboard)
        self.dashboard_controller.start()

    def show_pos(self):
        self.window.stack.setCurrentWidget(self.pos_controller.view)
        self.window.set_active_button(self.window.btn_pos)
        self.pos_controller.view.txt_codigo.setFocus()

    def show_inventario(self):
        self.window.stack.setCurrentWidget(self.inventario_controller.view)
        self.window.set_active_button(self.window.btn_inventario)
        self.inventario_controller.start()

    def show_actores(self):
        self.window.stack.setCurrentWidget(self.actores_controller.view)
        self.window.set_active_button(self.window.btn_actores)
        self.actores_controller.start()

    def start(self):
        # Al arrancar, mostrar el dashboard y comenzar a cargar datos
        self.dashboard_controller.start()
        self.window.showMaximized()
