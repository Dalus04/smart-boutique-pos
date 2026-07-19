from PySide6.QtCore import QObject, QThread, Signal, QTimer
from PySide6.QtWidgets import QToolTip, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QPushButton
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle
import numpy as np

from views.dashboard_view import DashboardView
from utils.ui_helpers import register_theme_observer, get_palette
from config.db import SessionLocal
from services.analitica import AnaliticaService
from services.mineria import MineriaService
from utils.signals import global_signals

class NumberAnimator(QObject):
    def __init__(self, label, end_val, format_func):
        super().__init__()
        self.label = label
        self.end_val = end_val
        self.format_func = format_func
        self.current_val = 0.0
        self.steps = 20
        self.step_val = end_val / self.steps if self.steps > 0 else 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(25) # 500ms aprox total
        
    def _update(self):
        self.current_val += self.step_val
        self.steps -= 1
        if self.steps <= 0:
            self.current_val = self.end_val
            self.timer.stop()
            self.deleteLater()
            
        self.label.setText(self.format_func(self.current_val))

class AnaliticaWorker(QThread):
    datos_cargados = Signal(dict)
    error = Signal(str)
    
    def __init__(self, periodo: str):
        super().__init__()
        self.periodo = periodo

    def run(self):
        db = SessionLocal()
        try:
            mapa = {
                "Hoy": "hoy",
                "Semana": "7_dias",
                "Mes": "mes",
                "Año": "anio"
            }
            p = mapa.get(self.periodo, "7_dias")
            
            metricas = AnaliticaService.obtener_metricas_completas(db, p)
            reglas = MineriaService.obtener_mejores_reglas(limit=3)
            
            from models.catalogo import Producto
            reglas_nom = []
            for a_id, c_id, conf in reglas:
                a_nom = db.query(Producto.nombre).filter(Producto.idProducto == a_id).scalar()
                c_nom = db.query(Producto.nombre).filter(Producto.idProducto == c_id).scalar()
                reglas_nom.append((a_nom, c_nom, conf))
                
            metricas["reglas"] = reglas_nom
            self.datos_cargados.emit(metricas)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            db.close()

class DashboardController(QObject):
    def __init__(self):
        super().__init__()
        self.view = DashboardView()
        self.worker = None
        self.datos_cache = None
        self.animators = []
        register_theme_observer(self.on_theme_changed)
        
        self.view.btn_group_periodo.buttonClicked.connect(self.start)

    def start(self):
        if self.worker and self.worker.isRunning():
            return
            
        # Limpiar animadores previos
        for anim in self.animators:
            try:
                anim.timer.stop()
                anim.deleteLater()
            except RuntimeError:
                pass
        self.animators.clear()
            
        self.view.chart_placeholder.setText("Calculando métricas en segundo plano...")
        btn = self.view.btn_group_periodo.checkedButton()
        periodo = btn.text() if btn else "Semana"
        
        self.worker = AnaliticaWorker(periodo)
        self.worker.datos_cargados.connect(self._on_datos_cargados)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _set_kpi_ui(self, lbl_val, lbl_var, kpi_data, format_func=str, invert_color=False):
        anim = NumberAnimator(lbl_val, kpi_data["valor"], format_func)
        self.animators.append(anim)
        
        var = kpi_data["var"]
        if abs(var) < 0.1:
            lbl_var.setText(f"≈ 0.00%")
            lbl_var.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        else:
            flecha = "↑" if var > 0 else "↓"
            color = "#27ae60" if var > 0 else "#c62828"
            if invert_color: 
                color = "#27ae60" if var < 0 else "#c62828"
            lbl_var.setText(f"{flecha} {abs(var):.2f}% vs Anterior")
            lbl_var.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

    def _on_datos_cargados(self, datos):
        self.datos_cache = datos
        kpis = datos["kpis"]
        
        # Tarjetas KPI
        self._set_kpi_ui(self.view.lbl_ventas_val, self.view.lbl_ventas_var, kpis["ventas"], lambda x: f"${x:,.2f}")
        self._set_kpi_ui(self.view.lbl_utilidad_val, self.view.lbl_utilidad_var, kpis["utilidad"], lambda x: f"${x:,.2f}")
        self._set_kpi_ui(self.view.lbl_margen_val, self.view.lbl_margen_var, kpis["margen"], lambda x: f"{x:.1f}%")
        self._set_kpi_ui(self.view.lbl_clientes_val, self.view.lbl_clientes_var, kpis["clientes"], lambda x: str(int(x)))

        # Proyección Mensual
        proyeccion = datos.get("proyeccion_mes", 0)
        ventas_actual = kpis["ventas"]["valor"]
        anim_proy = NumberAnimator(self.view.lbl_proyeccion_val, proyeccion, lambda x: f"${x:,.2f}")
        self.animators.append(anim_proy)
        prog_proy = int((ventas_actual / proyeccion * 100) if proyeccion > 0 else 0)
        self.view.progress_proyeccion.setValue(min(prog_proy, 100))

        # Health Score
        score = 0
        if kpis["utilidad"]["valor"] > 0: score += 30
        if kpis["ventas"]["var"] >= 0: score += 30
        
        salud = datos.get("salud_inventario", {})
        criticos = salud.get("Crítico", {}).get("items", 0)
        
        if criticos == 0:
            score += 40
        elif criticos <= 5:
            score += 20
        
        if score >= 80:
            estado_txt = "Excelente"
            color_est = "#27ae60"
        elif score >= 50:
            estado_txt = "Regular"
            color_est = "#f39c12"
        else:
            estado_txt = "Atención Requerida"
            color_est = "#e74c3c"
            
        self.view.lbl_h_estado.setText(estado_txt)
        self.view.lbl_h_estado.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color_est}; border: none;")
        self.view.progress_health.setValue(score)
        self.view.lbl_health_score.setText(f"{score}/100")

        # Generar Insights Accionables
        self._renderizar_insights(datos)

        # Evaluar historial para Gráficos
        tendencia = datos["charts"].get("tendencia", [])
        if len(tendencia) < 2:
            self.view.stacked_widget.setCurrentIndex(1)
            self.view.lbl_fb_msg.setText(f"Ventas consolidadas en este periodo: ${ventas_actual:,.2f}. Salud actual: {estado_txt}.")
        else:
            self.view.stacked_widget.setCurrentIndex(0)
            self._render_chart(datos["charts"])

    def _on_error(self, error_msg):
        self.view.chart_placeholder.setText(f"Error al cargar datos: {error_msg}")

    def _renderizar_insights(self, datos):
        while self.view.scroll_layout.count():
            item = self.view.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        insights = MineriaService.obtener_insights(datos)
        paleta = get_palette()
        
        for inv in insights:
            frame = QFrame()
            
            if inv["tipo"] == "resumen":
                bg_color = "rgba(42, 130, 218, 0.1)" # Azul suave
                border_color = "#2a82da"
            else:
                bg_color = {
                    "oportunidad": "rgba(39, 174, 96, 0.1)", 
                    "riesgo": "rgba(231, 76, 60, 0.1)", 
                    "tarea": "rgba(41, 128, 185, 0.1)"
                }.get(inv["tipo"], paleta["bg_element"])
                
                border_color = {
                    "oportunidad": "#27ae60", 
                    "riesgo": "#e74c3c", 
                    "tarea": "#2980b9"
                }.get(inv["tipo"], paleta["border"])
            
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                    padding: 4px;
                }}
            """)
            main_layout = QVBoxLayout(frame)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(5)
            
            # Fila de icono y mensaje
            h_layout = QHBoxLayout()
            lbl_icon = QLabel(inv["icono"])
            lbl_icon.setStyleSheet("font-size: 20px; border: none; background: transparent;")
            lbl_icon.setAlignment(Qt.AlignmentFlag.AlignTop)
            
            lbl_msg = QLabel(inv["mensaje"])
            lbl_msg.setWordWrap(True)
            if inv["tipo"] == "resumen":
                lbl_msg.setStyleSheet(f"color: {paleta['text_primary']}; font-size: 14px; font-weight: bold; border: none; background: transparent;")
            else:
                lbl_msg.setStyleSheet(f"color: {paleta['text_primary']}; font-size: 13px; border: none; background: transparent;")
            
            h_layout.addWidget(lbl_icon)
            h_layout.addWidget(lbl_msg, stretch=1)
            main_layout.addLayout(h_layout)
            
            # Botón accionable si existe
            if "accion_texto" in inv and "accion_target" in inv:
                btn_layout = QHBoxLayout()
                btn_layout.addStretch()
                btn_accion = QPushButton(inv["accion_texto"])
                btn_accion.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_accion.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {border_color};
                        color: #ffffff;
                        border-radius: 4px;
                        padding: 4px 12px;
                        font-weight: bold;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {paleta['text_primary']};
                    }}
                """)
                # Capturar el target usando parametro por defecto en lambda
                btn_accion.clicked.connect(lambda checked=False, tgt=inv["accion_target"]: global_signals.navegar_a_modulo.emit(tgt))
                btn_layout.addWidget(btn_accion)
                main_layout.addLayout(btn_layout)
            
            self.view.scroll_layout.addWidget(frame)
            
        self.view.scroll_layout.addStretch()

    def _render_chart(self, charts):
        for i in reversed(range(self.view.chart_layout.count())): 
            widget_to_remove = self.view.chart_layout.itemAt(i).widget()
            self.view.chart_layout.removeWidget(widget_to_remove)
            if widget_to_remove:
                widget_to_remove.setParent(None)

        paleta = get_palette()
        fig = Figure(figsize=(12, 4), dpi=100)
        fig.patch.set_facecolor(paleta["bg_app"]) 
        
        ax1 = fig.add_subplot(131)
        ax2 = fig.add_subplot(132)
        ax3 = fig.add_subplot(133)

        for ax in [ax1, ax2, ax3]:
            ax.set_facecolor(paleta["bg_element"])
            ax.tick_params(colors=paleta["text_primary"])
            for spine in ax.spines.values():
                spine.set_color(paleta["border"])

        # 1. TENDENCIA
        tendencia = charts["tendencia"]
        if tendencia:
            meses = [t["mes"] for t in tendencia]
            totales = [t["total_vendido"] for t in tendencia]
            
            # Línea principal
            ax1.plot(meses, totales, marker='o', color="#2a82da", linewidth=2, label='Ventas')
            
            # Línea de tendencia punteada (Regresión Lineal)
            if len(totales) > 1:
                x = np.arange(len(meses))
                z = np.polyfit(x, totales, 1)
                p = np.poly1d(z)
                ax1.plot(meses, p(x), color="#e74c3c", linestyle="--", linewidth=1.5, alpha=0.8, label='Tendencia')
                ax1.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=paleta["text_primary"])
                
            ax1.set_title("Recaudación y Tendencia", color=paleta["text_primary"], pad=10)
            ax1.tick_params(axis='x', labelrotation=45, labelsize=8)
            ax1.grid(color=paleta["border"], linestyle='-', linewidth=0.5, axis='y', alpha=0.5)
        else:
            ax1.text(0.5, 0.5, "Sin datos", color=paleta["text_secondary"], ha='center', va='center')

        # 2. CATEGORÍAS
        categorias = charts["categorias"]
        if categorias:
            cats = [c["categoria"] for c in categorias]
            ventas_cat = [c["precio_total"] for c in categorias]
            wedges, texts, autotexts = ax2.pie(
                ventas_cat, 
                labels=cats, 
                startangle=90, 
                autopct='%1.1f%%',
                textprops={'color': paleta["text_primary"], 'fontsize': 8}
            )
            for autotext in autotexts:
                autotext.set_color(paleta["text_primary"])
                autotext.set_fontsize(8)
                
            centre_circle = Circle((0,0),0.70,fc=paleta["bg_element"])
            ax2.add_artist(centre_circle)
            ax2.set_title("Distribución de Ventas", color=paleta["text_primary"], pad=10)
            for spine in ax2.spines.values(): spine.set_visible(False)
        else:
            ax2.text(0.5, 0.5, "Sin datos", color=paleta["text_secondary"], ha='center', va='center')

        # 3. TOP PRODUCTOS
        ranking = charts["ranking"]
        if ranking:
            nombres = [r["nombre"] for r in ranking][::-1]
            cants = [r["cantidad_vendida"] for r in ranking][::-1]
            totales = [r["total_recaudado"] for r in ranking][::-1]
            
            labels = [f"{c} u. | ${t:,.0f}" for c, t in zip(cants, totales)]
            bars = ax3.barh(nombres, cants, color="#27ae60")
            
            for bar, label in zip(bars, labels):
                width = bar.get_width()
                ax3.text(width, bar.get_y() + bar.get_height()/2, f' {label}',
                         va='center', ha='left', color=paleta['text_primary'], fontsize=8)
                         
            ax3.set_title("Top Productos", color=paleta["text_primary"], pad=10)
            ax3.tick_params(axis='y', labelsize=8)
            ax3.grid(color=paleta["border"], linestyle='-', linewidth=0.5, axis='x', alpha=0.5)
            ax3.set_xlim(right=ax3.get_xlim()[1] * 1.3)
        else:
            ax3.text(0.5, 0.5, "Sin datos", color=paleta["text_secondary"], ha='center', va='center')

        fig.tight_layout()
        canvas = FigureCanvas(fig)
        self.view.chart_layout.addWidget(canvas)

    def on_theme_changed(self):
        if self.datos_cache:
            self._render_chart(self.datos_cache["charts"])

