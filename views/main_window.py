from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QLabel
from PySide6.QtCore import Qt
import utils.ui_helpers as ui

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

        self.btn_actores = QPushButton(" Clientes/Prov.")
        self.btn_actores.setCheckable(True)

        self.btn_compras = QPushButton(" Compras")
        self.btn_compras.setCheckable(True)

        self.nav_buttons = [self.btn_dashboard, self.btn_pos, self.btn_inventario, self.btn_actores, self.btn_compras]
        for btn in self.nav_buttons:
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Botón Conmutador de Tema
        self.btn_theme_toggle = ui.crear_boton("☀️ Modo Claro", tipo="secundario")
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.btn_theme_toggle)

        # Stack central para intercambiar vistas
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #121212;")

        # Agregar componentes al layout principal
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)
        
        # Inicializar tema de la aplicación
        self.aplicar_tema()

    def set_active_button(self, active_btn):
        for btn in self.nav_buttons:
            btn.setChecked(btn == active_btn)

    def toggle_theme(self):
        if ui.CURRENT_THEME == "dark":
            ui.set_theme("light")
        else:
            ui.set_theme("dark")
        self.aplicar_tema()

    def aplicar_tema(self):
        paleta = ui.get_palette()
        
        if ui.CURRENT_THEME == "dark":
            self.btn_theme_toggle.setText("☀️ Modo Claro")
        else:
            self.btn_theme_toggle.setText("🌙 Modo Oscuro")
            
        # Aplicar estilo base a nivel de ventana para herencia cromática limpia
        self.setStyleSheet(f"""
            QMainWindow, QStackedWidget {{
                background-color: {paleta['bg_app']};
            }}
            QLabel {{
                color: {paleta['text_primary']};
                background: transparent;
            }}
            QLabel[theme_color="secondary"] {{
                color: {paleta['text_secondary']};
            }}
            QGroupBox {{
                color: {paleta['text_primary']};
            }}
            QAbstractSpinBox {{
                background-color: {paleta['bg_element']};
                border: 1px solid {paleta['border']};
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
                color: {paleta['text_primary']};
            }}
            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
                border: none;
            }}
            QListView {{
                background-color: {paleta['bg_element']};
                color: {paleta['text_primary']};
                border: 1px solid {paleta['border']};
                selection-background-color: {paleta['border_focus']};
                selection-color: #ffffff;
            }}
            QListView::item {{
                background-color: {paleta['bg_element']};
                color: {paleta['text_primary']};
                padding: 6px;
            }}
            QListView::item:selected {{
                background-color: {paleta['border_focus']};
                color: #ffffff;
            }}
            QDialog, QMessageBox {{
                background-color: {paleta['bg_app']};
                color: {paleta['text_primary']};
            }}
            QDialog QLabel, QMessageBox QLabel {{
                color: {paleta['text_primary']};
                background: transparent;
            }}
            QDialog QPushButton, QMessageBox QPushButton {{
                background-color: {paleta['hover']};
                color: {paleta['text_primary']};
                border: 1px solid {paleta['border']};
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: bold;
                font-size: 13px;
            }}
            QDialog QPushButton:hover, QMessageBox QPushButton:hover {{
                background-color: {paleta['border_focus']};
                color: #ffffff;
            }}
        """)
        
        self.stack.setStyleSheet(f"background-color: {paleta['bg_app']};")
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {paleta['bg_app']};
                border-right: 1px solid {paleta['border']};
            }}
            QPushButton {{
                background-color: transparent;
                color: {paleta['text_secondary']};
                border: none;
                padding: 12px 20px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {paleta['hover']};
                color: {paleta['text_primary']};
            }}
            QPushButton:checked {{
                background-color: {paleta['border_focus']};
                color: #ffffff;
                font-weight: bold;
            }}
        """)
        
        # Modificar título principal también
        title_label = self.sidebar.findChild(QLabel)
        if title_label:
            title_label.setStyleSheet(f"color: {paleta['text_primary']}; font-size: 18px; font-weight: bold; padding: 10px 10px 20px 10px; background: transparent;")
            
        for widget in self.findChildren(QWidget):
            factory_type = widget.property("factory_type")
            if factory_type == "input":
                ui.aplicar_estilo_input(widget, paleta)
            elif factory_type == "combo":
                ui.aplicar_estilo_combo(widget, paleta)
            elif factory_type == "boton":
                ui.aplicar_estilo_boton(widget, paleta)
            elif factory_type == "tabla":
                ui.aplicar_estilo_tabla(widget, paleta)
            elif factory_type == "tarjeta_kpi":
                ui.aplicar_estilo_tarjeta_kpi(widget, paleta)
            elif factory_type == "panel":
                ui.aplicar_estilo_panel(widget, paleta)
            elif factory_type == "groupbox":
                ui.aplicar_estilo_groupbox(widget, paleta)
            elif factory_type == "tabwidget":
                ui.aplicar_estilo_tabwidget(widget, paleta)
            elif factory_type == "rec_card":
                ui.aplicar_estilo_tarjeta_rec(widget, paleta)
            elif factory_type == "qty_btn":
                ui.aplicar_estilo_qty_btn(widget, paleta)
