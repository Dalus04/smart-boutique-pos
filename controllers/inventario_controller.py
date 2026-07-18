import csv
from PySide6.QtCore import QObject, QThread, Signal, QTimer, Qt
from PySide6.QtWidgets import QTableWidgetItem, QFileDialog, QMessageBox
from views.inventario_view import InventarioView
from config.db import SessionLocal
from models.catalogo import Producto, Categoria
from models.suministro import Inventario
from services.prediccion import PrediccionService
from utils.ui_helpers import aplicar_estilo_tarjeta_kpi, get_palette
from utils.signals import global_signals

class NumericItem(QTableWidgetItem):
    """Subclase de QTableWidgetItem para ordenar correctamente valores numéricos."""
    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            try:
                val_self = float(self.text().split()[0])
                val_other = float(other.text().split()[0])
                return val_self < val_other
            except ValueError:
                return self.text() < other.text()
        return super().__lt__(other)

class InventarioWorker(QThread):
    datos_cargados = Signal(list)
    error = Signal(str)

    def __init__(self, dias_entrega):
        super().__init__()
        self.dias_entrega = dias_entrega

    def run(self):
        db = SessionLocal()
        try:
            resultados = []
            productos = db.query(Producto, Categoria, Inventario).\
                join(Categoria, Producto.idCategoria == Categoria.idCategoria).\
                outerjoin(Inventario, Producto.idProducto == Inventario.idProducto).\
                all()
                
            for prod, cat, inv in productos:
                evaluacion = PrediccionService.evaluar_producto(db, prod.idProducto, self.dias_entrega)
                fecha_str = inv.fechaActualizacion.strftime("%d/%m/%Y %H:%M") if inv and inv.fechaActualizacion else "N/A"
                resultados.append({
                    "id": prod.idProducto,
                    "categoria": cat.nombreCategoria,
                    "nombre": prod.nombre,
                    "stock_actual": evaluacion["stock_actual"],
                    "velocidad": evaluacion["velocidad_venta_diaria"],
                    "ultima_actualizacion": fecha_str,
                    "riesgo": evaluacion["riesgo"]
                })
                
            self.datos_cargados.emit(resultados)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            db.close()

class InventarioController(QObject):
    def __init__(self):
        super().__init__()
        self.view = InventarioView()
        self.worker = None
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        
        # Conectar señales
        self.debounce_timer.timeout.connect(self.cargar_datos)
        self.view.spin_dias_entrega.valueChanged.connect(self.on_dias_entrega_changed)
        self.view.combo_categoria.currentTextChanged.connect(self.aplicar_filtros)
        self.view.combo_alerta.currentTextChanged.connect(self.aplicar_filtros)
        self.view.txt_buscar.textChanged.connect(self.aplicar_filtros)
        
        # Nuevos Botones
        self.view.btn_actualizar.clicked.connect(self.cargar_datos)
        self.view.btn_limpiar.clicked.connect(self.limpiar_filtros)
        self.view.btn_exportar.clicked.connect(self.exportar_csv)
        
        # Hot-reloading
        global_signals.inventario_actualizado.connect(self.cargar_datos)
        
        self.datos_completos = []

    def on_dias_entrega_changed(self):
        self.debounce_timer.start(300)

    def cargar_datos(self):
        self.view.progress_bar.show()
        self.view.spin_dias_entrega.setEnabled(False)
        self.view.btn_actualizar.setEnabled(False)
        
        dias_entrega = self.view.spin_dias_entrega.value()
        
        self.worker = InventarioWorker(dias_entrega)
        self.worker.datos_cargados.connect(self.on_datos_cargados)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_datos_cargados(self, datos):
        self.datos_completos = datos
        self.view.progress_bar.hide()
        self.view.spin_dias_entrega.setEnabled(True)
        self.view.btn_actualizar.setEnabled(True)
        
        self.poblar_tabla()
        
        # Actualizar opciones del filtro de categoría
        categorias_unicas = sorted(list(set([d["categoria"] for d in datos])))
        cat_actual = self.view.combo_categoria.currentText()
        
        self.view.combo_categoria.currentTextChanged.disconnect(self.aplicar_filtros)
        self.view.combo_categoria.clear()
        self.view.combo_categoria.addItem("Todas")
        self.view.combo_categoria.addItems(categorias_unicas)
        
        index = self.view.combo_categoria.findText(cat_actual)
        if index >= 0:
            self.view.combo_categoria.setCurrentIndex(index)
            
        self.view.combo_categoria.currentTextChanged.connect(self.aplicar_filtros)
        
        # Llamar a aplicar_filtros que actualizará los KPIs reactivos
        self.aplicar_filtros()

    def on_error(self, error_msg):
        self.view.progress_bar.hide()
        self.view.spin_dias_entrega.setEnabled(True)
        self.view.btn_actualizar.setEnabled(True)
        print(f"Error cargando inventario: {error_msg}")

    def poblar_tabla(self):
        self.view.tabla.setSortingEnabled(False)
        self.view.tabla.setRowCount(0)
        self.view.tabla.setRowCount(len(self.datos_completos))
        
        for row, dato in enumerate(self.datos_completos):
            item_id = NumericItem(str(dato["id"]))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.view.tabla.setItem(row, 0, item_id)
            
            item_cat = QTableWidgetItem(dato["categoria"])
            self.view.tabla.setItem(row, 1, item_cat)
            
            item_prod = QTableWidgetItem(dato["nombre"])
            self.view.tabla.setItem(row, 2, item_prod)
            
            item_stock = NumericItem(str(dato["stock_actual"]))
            item_stock.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.view.tabla.setItem(row, 3, item_stock)
            
            vel_str = f"{dato['velocidad']:.2f} uds/día"
            item_vel = NumericItem(vel_str)
            item_vel.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_vel.setToolTip("Ritmo promedio de ventas calculado en los últimos 30 días.")
            self.view.tabla.setItem(row, 4, item_vel)
            
            item_fecha = QTableWidgetItem(dato["ultima_actualizacion"])
            item_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.view.tabla.setItem(row, 5, item_fecha)
            
            riesgo_original = dato["riesgo"]
            riesgo_prescriptivo = ""
            tooltip_riesgo = ""
            
            if riesgo_original == "Riesgo Alto":
                riesgo_prescriptivo = "🔴 Reposición urgente"
                tooltip_riesgo = "El stock se agotará antes de que llegue el pedido."
            elif riesgo_original == "Riesgo Medio":
                riesgo_prescriptivo = "🟡 Alerta temprana"
                tooltip_riesgo = "El stock cubre la demanda pero está por debajo del margen de seguridad."
            else:
                riesgo_prescriptivo = "🟢 Stock saludable"
                tooltip_riesgo = "Nivel de stock óptimo para afrontar el tiempo de espera."
                
            item_riesgo = QTableWidgetItem(riesgo_prescriptivo)
            item_riesgo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_riesgo.setToolTip(tooltip_riesgo)
            item_riesgo.setData(Qt.ItemDataRole.UserRole, riesgo_original)
            self.view.tabla.setItem(row, 6, item_riesgo)
            
        self.view.tabla.setSortingEnabled(True)

    def aplicar_filtros(self):
        cat_filtro = self.view.combo_categoria.currentText()
        alerta_filtro = self.view.combo_alerta.currentText()
        busqueda = self.view.txt_buscar.text().strip().lower()
        is_digit = busqueda.isdigit()
        
        for row in range(self.view.tabla.rowCount()):
            self.view.tabla.setRowHidden(row, False)
            
            item_id = self.view.tabla.item(row, 0)
            item_cat = self.view.tabla.item(row, 1)
            item_nom = self.view.tabla.item(row, 2)
            item_riesgo = self.view.tabla.item(row, 5)
            
            if not item_cat or not item_riesgo or not item_id or not item_nom:
                continue
                
            ocultar = False
            
            if cat_filtro != "Todas" and item_cat.text() != cat_filtro:
                ocultar = True
                
            if alerta_filtro != "Todas":
                riesgo_original = item_riesgo.data(Qt.ItemDataRole.UserRole)
                if riesgo_original != alerta_filtro:
                    ocultar = True
                    
            if busqueda:
                if is_digit:
                    if busqueda not in item_id.text():
                        ocultar = True
                else:
                    if busqueda not in item_nom.text().lower():
                        ocultar = True
                
            if ocultar:
                self.view.tabla.setRowHidden(row, True)
                
        # Recalcular dinámicamente las tarjetas superiores
        self.actualizar_kpis_dinamicos()

    def actualizar_kpis_dinamicos(self):
        total_productos = 0
        saludables = 0
        urgentes = 0
        
        for row in range(self.view.tabla.rowCount()):
            if not self.view.tabla.isRowHidden(row):
                total_productos += 1
                item_riesgo = self.view.tabla.item(row, 5)
                if item_riesgo:
                    riesgo_original = item_riesgo.data(Qt.ItemDataRole.UserRole)
                    if riesgo_original == "Sin Riesgo":
                        saludables += 1
                    elif riesgo_original == "Riesgo Alto":
                        urgentes += 1
                        
        self.view.lbl_kpi_total.setText(str(total_productos))
        self.view.lbl_kpi_saludable.setText(str(saludables))
        self.view.lbl_kpi_urgente.setText(str(urgentes))
        
        if urgentes > 0:
            self.view.kpi_frame_urgente.setProperty("kpi_color_borde", "#ff5252")
            self.view.kpi_frame_urgente.setProperty("kpi_danger", True)
        else:
            self.view.kpi_frame_urgente.setProperty("kpi_color_borde", "#3d3d3d")
            self.view.kpi_frame_urgente.setProperty("kpi_danger", False)
            
        aplicar_estilo_tarjeta_kpi(self.view.kpi_frame_urgente, get_palette())

    def limpiar_filtros(self):
        self.view.txt_buscar.clear()
        self.view.combo_categoria.setCurrentIndex(0)
        self.view.combo_alerta.setCurrentIndex(0)
        self.view.spin_dias_entrega.setValue(7)
        # El textChanged / currentTextChanged llamará a aplicar_filtros()
        
    def exportar_csv(self):
        if self.view.tabla.rowCount() == 0:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self.view,
            "Exportar Inventario",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                headers = [self.view.tabla.horizontalHeaderItem(col).text() for col in range(self.view.tabla.columnCount())]
                writer.writerow(headers)
                
                for row in range(self.view.tabla.rowCount()):
                    if self.view.tabla.isRowHidden(row):
                        continue
                    row_data = [self.view.tabla.item(row, col).text() if self.view.tabla.item(row, col) else "" for col in range(self.view.tabla.columnCount())]
                    writer.writerow(row_data)
                    
            QMessageBox.information(self.view, "Exportación Exitosa", f"Se exportó correctamente a:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Fallo al exportar el archivo:\n{str(e)}")

    def start(self):
        if len(self.datos_completos) == 0:
            self.cargar_datos()
