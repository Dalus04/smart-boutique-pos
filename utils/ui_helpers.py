from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView, QLineEdit, QComboBox, QPushButton, QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor

DARK_PALETTE = {
    "bg_app": "#121212",
    "bg_element": "#1e1e1e",
    "bg_alt": "#252525",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
    "border": "#333333",
    "border_focus": "#2a82da",
    "hover": "#2d2d2d",
    "disabled_bg": "#1a1a1a",
    "disabled_text": "#777777",
    "gridline": "#333333",
    "header_bg": "#2d2d2d",
    "bg_green_alpha": "rgba(76, 175, 80, 0.05)",
    "border_green_alpha": "rgba(76, 175, 80, 0.2)",
    "bg_highlight": "#1a3e5c"
}

LIGHT_PALETTE = {
    "bg_app": "#f0f2f5",
    "bg_element": "#ffffff",
    "bg_alt": "#f9f9f9",
    "text_primary": "#333333",
    "text_secondary": "#666666",
    "border": "#e0e0e0",
    "border_focus": "#2a82da",
    "hover": "#f5f5f5",
    "disabled_bg": "#e9ecef",
    "disabled_text": "#adb5bd",
    "gridline": "#e0e0e0",
    "header_bg": "#e9ecef",
    "bg_green_alpha": "rgba(76, 175, 80, 0.08)",
    "border_green_alpha": "rgba(76, 175, 80, 0.3)",
    "bg_highlight": "#d0e8ff"
}

CURRENT_THEME = "dark"
THEME_CHANGED_CALLBACKS = []

def get_palette():
    global CURRENT_THEME
    return DARK_PALETTE if CURRENT_THEME == "dark" else LIGHT_PALETTE

def set_theme(theme_name):
    global CURRENT_THEME
    if theme_name in ["dark", "light"]:
        CURRENT_THEME = theme_name
        for cb in THEME_CHANGED_CALLBACKS:
            try:
                cb()
            except Exception as e:
                pass

def register_theme_observer(callback):
    THEME_CHANGED_CALLBACKS.append(callback)

# --- APLICADORES DE ESTILO (Refresco) ---

def aplicar_estilo_tabla(tabla, paleta):
    tabla.setStyleSheet(f"""
        QTableWidget {{
            background-color: {paleta['bg_element']};
            alternate-background-color: {paleta['bg_alt']};
            gridline-color: {paleta['gridline']};
            color: {paleta['text_primary']};
            border: none;
            border-radius: 8px;
            font-size: 14px;
        }}
        QHeaderView::section {{
            background-color: {paleta['header_bg']};
            color: {paleta['text_primary']};
            padding: 8px;
            border: 1px solid {paleta['border']};
            font-weight: bold;
            font-size: 14px;
        }}
        QTableWidget::item {{
            padding: 5px;
        }}
        QTableWidget::item:selected {{
            background-color: {paleta['border_focus']};
            color: #ffffff;
        }}
    """)
    
    # Refrescar backgrounds de los items existentes según el tema activo
    for r in range(tabla.rowCount()):
        item_zero = tabla.item(r, 0)
        es_resaltado = False
        if item_zero and item_zero.data(Qt.ItemDataRole.UserRole):
            es_resaltado = True
            
        brush = QBrush(QColor(paleta["bg_highlight"])) if es_resaltado else QBrush()
        
        for c in range(tabla.columnCount()):
            item = tabla.item(r, c)
            if item:
                item.setBackground(brush)

def aplicar_estilo_input(widget, paleta):
    widget.setStyleSheet(f"""
        QLineEdit {{
            background-color: {paleta['bg_element']};
            border: 1px solid {paleta['border']};
            border-radius: 4px;
            padding: 6px;
            font-size: 14px;
            color: {paleta['text_primary']};
        }}
        QLineEdit:focus {{
            border: 1px solid {paleta['border_focus']};
        }}
        QLineEdit:disabled {{
            background-color: {paleta['disabled_bg']};
            color: {paleta['disabled_text']};
            border: 1px solid {paleta['border']};
        }}
    """)

def aplicar_estilo_combo(widget, paleta):
    widget.setStyleSheet(f"""
        QComboBox {{
            background-color: {paleta['bg_element']};
            color: {paleta['text_primary']};
            border: 1px solid {paleta['border']};
            border-radius: 4px;
            padding: 6px;
            font-size: 14px;
        }}
        QComboBox:focus {{
            border: 1px solid {paleta['border_focus']};
        }}
        QComboBox QLineEdit {{
            background-color: {paleta['bg_element']};
            color: {paleta['text_primary']};
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {paleta['bg_element']};
            color: {paleta['text_primary']};
            selection-background-color: {paleta['border_focus']};
            selection-color: #ffffff;
        }}
        QComboBox QAbstractItemView::item {{
            background-color: {paleta['bg_element']};
            color: {paleta['text_primary']};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {paleta['border_focus']};
            color: #ffffff;
        }}
    """)

def aplicar_estilo_boton(widget, paleta):
    tipo = widget.property("btn_tipo")
    
    colores_dark = {
        "primario": {"bg": "#2a82da", "hover": "#3b93eb"},
        "exito": {"bg": "#2e7d32", "hover": "#3e8d42"},
        "peligro": {"bg": "#d9534f", "hover": "#c9302c"},
        "secundario": {"bg": "#3d3d3d", "hover": "#4d4d4d"}
    }
    colores_light = {
        "primario": {"bg": "#1976d2", "hover": "#1565c0"},
        "exito": {"bg": "#388e3c", "hover": "#2e7d32"},
        "peligro": {"bg": "#d32f2f", "hover": "#c62828"},
        "secundario": {"bg": "#e0e0e0", "hover": "#d5d5d5", "text": "#333333"}
    }
    
    colores = colores_dark if CURRENT_THEME == "dark" else colores_light
    color_cfg = colores.get(tipo, colores["primario"])
    
    text_color = color_cfg.get("text", "#ffffff")
    
    widget.setStyleSheet(f"""
        QPushButton {{
            background-color: {color_cfg['bg']}; 
            color: {text_color};
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
            background-color: {paleta['disabled_bg']};
            color: {paleta['disabled_text']};
        }}
    """)

def aplicar_estilo_tarjeta_kpi(widget, paleta):
    color_borde = widget.property("kpi_color_borde")
    is_danger = widget.property("kpi_danger")
    
    bg = "#c62828" if is_danger else paleta['bg_element']
    val_color = "#ffffff" if is_danger else paleta['text_primary']
    tit_color = "#ffcdd2" if is_danger else paleta['text_secondary']
    
    widget.setStyleSheet(f"""
        QFrame {{
            background-color: {bg};
            border-radius: 8px;
            border-left: 4px solid {color_borde};
            padding: 10px;
        }}
    """)
    for lbl in widget.findChildren(QLabel):
        if lbl.property("kpi_lbl_type") == "valor":
            lbl.setStyleSheet(f"color: {val_color}; font-size: 28px; font-weight: bold; border: none; background: transparent;")
        elif lbl.property("kpi_lbl_type") == "titulo":
            lbl.setStyleSheet(f"color: {tit_color}; font-size: 14px; font-weight: bold; border: none; background: transparent;")

def aplicar_estilo_panel(widget, paleta):
    tipo = widget.property("panel_tipo")
    if tipo == "green":
        bg = paleta["bg_green_alpha"]
        border = paleta["border_green_alpha"]
    else:
        bg = paleta["bg_element"]
        border = paleta["border"]
        
    widget.setStyleSheet(f"""
        QFrame {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 8px;
        }}
    """)

def aplicar_estilo_tabwidget(widget, paleta):
    widget.setStyleSheet(f"""
        QTabWidget::panel {{
            border: 1px solid {paleta['border']};
            background-color: {paleta['bg_app']};
            border-radius: 8px;
        }}
        QTabBar::tab {{
            background-color: {paleta['bg_element']};
            color: {paleta['text_secondary']};
            border: 1px solid {paleta['border']};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
        }}
        QTabBar::tab:selected {{
            background-color: {paleta['border_focus']};
            color: #ffffff;
            border: 1px solid {paleta['border_focus']};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {paleta['hover']};
            color: {paleta['text_primary']};
        }}
    """)

def aplicar_estilo_groupbox(widget, paleta):
    border_color = paleta['border']
    text_color = paleta['text_primary']
    if widget.property("group_type") == "highlight":
        border_color = paleta['border_focus']
        text_color = paleta['border_focus']
        
    widget.setStyleSheet(f"""
        QGroupBox {{
            background-color: {paleta['bg_element']};
            border: 1px solid {border_color};
            border-radius: 8px;
            font-weight: bold;
            color: {text_color};
            margin-top: 10px;
            padding-top: 15px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 3px;
            color: {text_color};
        }}
    """)

# --- FACTORIES ---

def crear_tabla_estandar(columnas, editable=False, alt_row_colors=True, row_height=35):
    tabla = QTableWidget(0, len(columnas))
    tabla.setHorizontalHeaderLabels(columnas)
    
    if not editable:
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    tabla.setAlternatingRowColors(alt_row_colors)
    
    tabla.verticalHeader().setVisible(False)
    tabla.verticalHeader().setDefaultSectionSize(row_height)
    
    tabla.setProperty("factory_type", "tabla")
    aplicar_estilo_tabla(tabla, get_palette())
    
    return tabla

def crear_input_estandar(placeholder=""):
    input_widget = QLineEdit()
    input_widget.setPlaceholderText(placeholder)
    input_widget.setProperty("factory_type", "input")
    aplicar_estilo_input(input_widget, get_palette())
    return input_widget

def crear_combo_estandar(items=None):
    combo = QComboBox()
    if items:
        combo.addItems(items)
    combo.setProperty("factory_type", "combo")
    aplicar_estilo_combo(combo, get_palette())
    return combo

def crear_boton(texto, tipo="primario"):
    btn = QPushButton(texto)
    btn.setProperty("factory_type", "boton")
    btn.setProperty("btn_tipo", tipo)
    aplicar_estilo_boton(btn, get_palette())
    return btn

def crear_tarjeta_kpi(titulo, valor_inicial="0", color_borde="#2a82da"):
    frame = QFrame()
    frame.setProperty("factory_type", "tarjeta_kpi")
    frame.setProperty("kpi_color_borde", color_borde)
    
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(15, 10, 15, 10)
    
    lbl_valor = QLabel(str(valor_inicial))
    lbl_valor.setProperty("kpi_lbl_type", "valor")
    
    lbl_titulo = QLabel(titulo)
    lbl_titulo.setProperty("kpi_lbl_type", "titulo")
    
    layout.addWidget(lbl_valor)
    layout.addWidget(lbl_titulo)
    
    aplicar_estilo_tarjeta_kpi(frame, get_palette())
    
    return frame, lbl_valor

def aplicar_estilo_tarjeta_rec(widget, paleta):
    widget.setStyleSheet(f"""
        QWidget {{
            background-color: {paleta['bg_alt']};
            border: 1px solid {paleta['border']};
            border-radius: 6px;
        }}
    """)
    for lbl in widget.findChildren(QLabel):
        if lbl.property("rec_lbl_type") == "text":
            lbl.setStyleSheet(f"color: {paleta['text_primary']}; font-size: 14px; border: none; background: transparent;")
        elif lbl.property("rec_lbl_type") == "confianza":
            color = "#d1b894" if CURRENT_THEME == "dark" else "#8f6d3b"
            lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-style: italic; border: none; background: transparent;")

def aplicar_estilo_qty_btn(widget, paleta):
    widget.setStyleSheet(f"""
        QPushButton {{
            background-color: {paleta['bg_alt']};
            color: {paleta['text_primary']};
            font-weight: bold;
            border-radius: 4px;
            border: 1px solid {paleta['border']};
        }}
        QPushButton:hover {{
            background-color: {paleta['hover']};
        }}
    """)
