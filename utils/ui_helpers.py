from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView, QLineEdit, QComboBox, QPushButton, QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

def crear_tabla_estandar(columnas, editable=False, alt_row_colors=True, row_height=35):
    """
    Factory function to create a standardized QTableWidget with common styling and behavior.
    """
    tabla = QTableWidget(0, len(columnas))
    tabla.setHorizontalHeaderLabels(columnas)
    
    # Ergonomics & Behavior
    if not editable:
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    tabla.setAlternatingRowColors(alt_row_colors)
    
    # Hide vertical header and set default row height
    tabla.verticalHeader().setVisible(False)
    tabla.verticalHeader().setDefaultSectionSize(row_height)
    
    # Visual Styles (QSS)
    tabla.setStyleSheet("""
        QTableWidget {
            background-color: #1e1e1e;
            alternate-background-color: #252525;
            gridline-color: #333333;
            color: #ffffff;
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
    
    return tabla

def crear_input_estandar(placeholder=""):
    input_widget = QLineEdit()
    input_widget.setPlaceholderText(placeholder)
    input_widget.setStyleSheet("""
        QLineEdit {
            background-color: #1e1e1e;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 6px;
            font-size: 14px;
            color: #ffffff;
        }
        QLineEdit:focus {
            border: 1px solid #2a82da;
        }
        QLineEdit:disabled {
            background-color: #1a1a1a;
            color: #777777;
            border: 1px solid #2d2d2d;
        }
    """)
    return input_widget

def crear_combo_estandar(items=None):
    combo = QComboBox()
    if items:
        combo.addItems(items)
    combo.setStyleSheet("""
        QComboBox {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 6px;
            font-size: 14px;
        }
        QComboBox:focus {
            border: 1px solid #2a82da;
        }
        QComboBox QAbstractItemView {
            background-color: #1e1e1e;
            color: #ffffff;
            selection-background-color: #2a82da;
            selection-color: #ffffff;
        }
        QComboBox QAbstractItemView::item {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #2a82da;
            color: #ffffff;
        }
    """)
    return combo

def crear_boton(texto, tipo="primario"):
    btn = QPushButton(texto)
    colores = {
        "primario": {"bg": "#2a82da", "hover": "#3b93eb"},
        "exito": {"bg": "#2e7d32", "hover": "#3e8d42"},
        "peligro": {"bg": "#d9534f", "hover": "#c9302c"},
        "secundario": {"bg": "#3d3d3d", "hover": "#4d4d4d"}
    }
    
    color_cfg = colores.get(tipo, colores["primario"])
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color_cfg['bg']}; 
            color: #ffffff;
            border-radius: 4px; 
            padding: 8px 15px; 
            font-weight: bold; 
            font-size: 14px;
            border: none;
        }}
        QPushButton:hover {{ 
            background-color: {color_cfg['hover']}; 
        }}
        QPushButton:disabled {{
            background-color: #444444;
            color: #888888;
        }}
    """)
    return btn

def crear_tarjeta_kpi(titulo, valor_inicial="0", color_borde="#2a82da"):
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
    
    lbl_valor = QLabel(str(valor_inicial))
    lbl_valor.setStyleSheet("color: #ffffff; font-size: 28px; font-weight: bold;")
    
    lbl_titulo = QLabel(titulo)
    lbl_titulo.setStyleSheet("color: #a0a0a0; font-size: 14px; font-weight: bold;")
    
    layout.addWidget(lbl_valor)
    layout.addWidget(lbl_titulo)
    return frame, lbl_valor
