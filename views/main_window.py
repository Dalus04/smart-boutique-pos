from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QLabel
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Boutique POS")
        self.setMinimumSize(1024, 768)

        # Widget central de la ventana
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout horizontal: Sidebar (izquierda) + StackedWidget (derecha)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-right: 1px solid #2d2d2d;
            }
            QPushButton {
                background-color: transparent;
                color: #b0b0b0;
                border: none;
                padding: 12px 20px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #2a82da;
                color: #ffffff;
                font-weight: bold;
            }
        """)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(8)

        # Título del menú lateral
        title_label = QLabel("Smart POS")
        title_label.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold; padding: 10px 10px 20px 10px;")
        sidebar_layout.addWidget(title_label)

        # Botones de Navegación
        self.btn_dashboard = QPushButton(" Dashboard")
        self.btn_dashboard.setCheckable(True)
        self.btn_dashboard.setChecked(True)

        self.btn_pos = QPushButton(" Ventas (POS)")
        self.btn_pos.setCheckable(True)

        self.btn_inventario = QPushButton(" Inventario")
        self.btn_inventario.setCheckable(True)

        self.nav_buttons = [self.btn_dashboard, self.btn_pos, self.btn_inventario]
        for btn in self.nav_buttons:
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Stack central para intercambiar vistas
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #121212;")

        # Agregar componentes al layout principal
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

    def set_active_button(self, active_btn):
        for btn in self.nav_buttons:
            btn.setChecked(btn == active_btn)
