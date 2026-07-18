from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtWidgets import QTableWidgetItem, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QPushButton, QMessageBox
from PySide6.QtGui import QColor, QBrush
from views.pos_view import POSView, QuantityWidget
from views.notification_toast import NotificationToast
from config.db import SessionLocal
from models.catalogo import Producto, Categoria
from models.actores import Cliente
from models.pos import MedioPago
from models.suministro import Inventario
from services.mineria import MineriaService
from services.pos import POSService
from sqlalchemy import func

class POSController(QObject):
    def __init__(self):
        super().__init__()
        self.view = POSView()
        self.carrito = [] # {"producto": Producto, "cantidad": int}
        self.productos_db = {} # {idProducto: Producto}
        self.stock_db = {} # {idProducto: int}
        self.highlighted_prod_id = None

        # Inicialización de dependencias
        self._cargar_datos_maestros()
        self._entrenar_modelo_mineria()

        # Conectar eventos de la interfaz
        self.view.combo_categorias.currentIndexChanged.connect(self._filtrar_productos_por_categoria)
        self.view.txt_codigo.textChanged.connect(self._buscar_por_codigo)
        self.view.combo_productos.currentIndexChanged.connect(self._on_producto_combo_changed)
        self.view.btn_limpiar_busqueda.clicked.connect(self.limpiar_busqueda)
        self.view.btn_agregar.clicked.connect(self.agregar_seleccionado)
        self.view.btn_limpiar.clicked.connect(self.limpiar_carrito)
        self.view.btn_limpiar_cliente.clicked.connect(self.limpiar_cliente)
        self.view.btn_procesar.clicked.connect(self.procesar_venta)

        # Atajos de Teclado (Enter)
        from PySide6.QtWidgets import QLineEdit
        self.view.txt_codigo.returnPressed.connect(self.on_buscador_enter_pressed)
        self.view.combo_productos.lineEdit().returnPressed.connect(self.on_buscador_enter_pressed)
        qty_line_edit = self.view.spin_cantidad.findChild(QLineEdit)
        if qty_line_edit:
            qty_line_edit.returnPressed.connect(self.agregar_seleccionado)

    def _cargar_datos_maestros(self):
        db = SessionLocal()
        try:
            # Bloquear señales al limpiar y recargar para evitar ciclos infinitos
            self.view.combo_categorias.blockSignals(True)
            self.view.combo_cliente.blockSignals(True)
            self.view.combo_pago.blockSignals(True)

            self.view.combo_categorias.clear()
            self.view.combo_cliente.clear()
            self.view.combo_pago.clear()

            # Valores por defecto obligatorios
            self.view.combo_categorias.addItem("Todas", None)
            self.view.combo_cliente.addItem("Consumidor Final", None)

            # 1. Cargar Categorías
            categorias = db.query(Categoria).all()
            for cat in categorias:
                self.view.combo_categorias.addItem(cat.nombreCategoria, cat.idCategoria)

            # 2. Cargar Clientes (Cambiado de ID a Código)
            clientes = db.query(Cliente).all()
            for cli in clientes:
                self.view.combo_cliente.addItem(f"{cli.nombresCompletos} (Código: {cli.idCliente})", cli.idCliente)

            # Re-vincular modelo al completer de clientes
            self.view.cliente_completer.setModel(self.view.combo_cliente.model())

            # 3. Cargar Medios de Pago
            medios_pago = db.query(MedioPago).all()
            for mp in medios_pago:
                self.view.combo_pago.addItem(mp.nombreMedioPago, mp.idMedioPago)

            # 4. Cargar Productos y Stock Total
            productos = db.query(Producto).all()
            self.productos_db.clear()
            for prod in productos:
                self.productos_db[prod.idProducto] = prod
            
            # Obtener stock sumado por producto
            stock_results = db.query(Inventario.idProducto, func.sum(Inventario.cantidadDisponible)).group_by(Inventario.idProducto).all()
            self.stock_db.clear()
            for id_prod, stock_total in stock_results:
                self.stock_db[id_prod] = int(stock_total or 0)
                
            # Construir combo de productos inicial
            self._filtrar_productos_por_categoria()
        except Exception as e:
            print(f"Error al cargar datos maestros: {e}")
        finally:
            self.view.combo_categorias.blockSignals(False)
            self.view.combo_cliente.blockSignals(False)
            self.view.combo_pago.blockSignals(False)
            db.close()
            
    def _filtrar_productos_por_categoria(self):
        cat_id = self.view.combo_categorias.currentData()
        
        # Bloquear señal de cambio de producto para no disparar autocompletado/código
        self.view.combo_productos.blockSignals(True)
        self.view.combo_productos.clear()
        
        for prod_id, prod in self.productos_db.items():
            if cat_id is None or prod.idCategoria == cat_id:
                # Excluir stock de la presentación en el ComboBox
                text = f"{prod.nombre} - ${prod.precioLista:.2f}"
                self.view.combo_productos.addItem(text, prod_id)
                
        # Forzar estado sin selección (Index -1) para inicializar
        self.view.combo_productos.setCurrentIndex(-1)
        self.view.combo_productos.blockSignals(False)
        self.view.completer.setModel(self.view.combo_productos.model())
        
        # Forzar estado inicial de los campos del producto sin disparar feedbacks
        self._set_estado_inicial_campos_producto()

    def _set_estado_inicial_campos_producto(self):
        self.view.txt_codigo.blockSignals(True)
        self.view.txt_codigo.setText("")
        self.view.txt_codigo.blockSignals(False)
        self.view.lbl_stock.setText("Stock: --")
        self.view.btn_agregar.setEnabled(False)
        self.view.lbl_feedback.setText("")

    def _buscar_por_codigo(self, texto_codigo):
        texto_codigo = texto_codigo.strip()
        if not texto_codigo:
            self.view.combo_productos.setCurrentIndex(-1)
            return
            
        try:
            prod_id = int(texto_codigo)
            if prod_id in self.productos_db:
                # Si el producto existe, aseguramos que la categoría esté en "Todas" para que sea visible en el combo
                if self.view.combo_categorias.currentIndex() != 0:
                    self.view.combo_categorias.blockSignals(True)
                    self.view.combo_categorias.setCurrentIndex(0)
                    self._filtrar_productos_por_categoria()
                    self.view.combo_categorias.blockSignals(False)
                
                # Buscar y seleccionar en combo_productos
                for i in range(self.view.combo_productos.count()):
                    if self.view.combo_productos.itemData(i) == prod_id:
                        self.view.combo_productos.setCurrentIndex(i)
                        break
            else:
                self.view.combo_productos.setCurrentIndex(-1)
        except ValueError:
            self.view.combo_productos.setCurrentIndex(-1)

    def _on_producto_combo_changed(self, index):
        if index < 0:
            self._set_estado_inicial_campos_producto()
            return
            
        prod_id = self.view.combo_productos.itemData(index)
        if prod_id:
            # Sincronizar código bloqueando señales
            self.view.txt_codigo.blockSignals(True)
            self.view.txt_codigo.setText(str(prod_id))
            self.view.txt_codigo.blockSignals(False)
            self.view.btn_agregar.setEnabled(True) # Habilitar botón Agregar
            
            # Actualizar etiqueta de Stock dinámica
            stock = self.stock_db.get(prod_id, 0)
            self.view.lbl_stock.setText(f"Stock: {stock}")

            # Retroalimentación visual discreta al seleccionar producto
            prod = self.productos_db.get(prod_id)
            if prod:
                self.mostrar_feedback_seleccion(prod.nombre)

    def mostrar_feedback_seleccion(self, nombre):
        NotificationToast(self.view.window(), f"✓ Seleccionado: {nombre}")

    def mostrar_feedback_agregado(self, nombre):
        NotificationToast(self.view.window(), f"✓ Agregado al carrito: {nombre}")

    def _limpiar_feedback_si_igual(self, texto_esperado):
        pass

    def limpiar_busqueda(self):
        # Bloquear señales en categorías para evitar recargas intermedias
        self.view.combo_categorias.blockSignals(True)
        self.view.combo_categorias.setCurrentIndex(0) # "Todas"
        self.view.combo_categorias.blockSignals(False)
        
        self.view.spin_cantidad.setValue(1)
        self._filtrar_productos_por_categoria()

    def limpiar_cliente(self):
        # Reiniciar únicamente la selección de cliente a vacío (Placeholder)
        self.view.combo_cliente.setCurrentIndex(-1)

    def _entrenar_modelo_mineria(self):
        db = SessionLocal()
        try:
            MineriaService.entrenar_modelo(db, min_support=2, min_confidence=0.3)
        except Exception as e:
            pass
        finally:
            db.close()

    def on_buscador_enter_pressed(self):
        idx = self.view.combo_productos.currentIndex()
        if idx >= 0:
            self.view.spin_cantidad.setFocus()
            self.view.spin_cantidad.selectAll()
        else:
            NotificationToast(self.view.window(), "⚠ Producto no encontrado.")
            sender = self.sender()
            if sender == self.view.txt_codigo:
                self.view.txt_codigo.setFocus()
                self.view.txt_codigo.selectAll()
            elif sender == self.view.combo_productos.lineEdit():
                self.view.combo_productos.setFocus()
                self.view.combo_productos.lineEdit().selectAll()

    def agregar_seleccionado(self):
        idx = self.view.combo_productos.currentIndex()
        if idx < 0:
            return
        prod_id = self.view.combo_productos.itemData(idx)
        cantidad = self.view.spin_cantidad.value()
        
        if self.agregar_al_carrito(prod_id, cantidad):
            self.view.spin_cantidad.setValue(1)
            self.view.combo_productos.setFocus()
            if self.view.combo_productos.lineEdit():
                self.view.combo_productos.lineEdit().selectAll()

    def agregar_al_carrito(self, prod_id: int, cantidad_adicional: int = 1) -> bool:
        if prod_id not in self.productos_db:
            return False
            
        stock_disponible = self.stock_db.get(prod_id, 0)
        
        # Validar si ya está en carrito para considerar la cantidad acumulada
        cantidad_actual_en_carrito = 0
        for item in self.carrito:
            if item["producto"].idProducto == prod_id:
                cantidad_actual_en_carrito = item["cantidad"]
                break
                
        nueva_cantidad_total = cantidad_actual_en_carrito + cantidad_adicional
        
        if nueva_cantidad_total > stock_disponible:
            QMessageBox.warning(self.view, "Stock Insuficiente", f"No hay stock suficiente. Disponible: {stock_disponible}")
            return False
        
        if cantidad_actual_en_carrito > 0:
            for item in self.carrito:
                if item["producto"].idProducto == prod_id:
                    item["cantidad"] = nueva_cantidad_total
                    break
        else:
            self.carrito.append({"producto": self.productos_db[prod_id], "cantidad": cantidad_adicional})
            
        # Feedback visual al agregar exitosamente
        self.mostrar_feedback_agregado(self.productos_db[prod_id].nombre)
        # Indicar highlight
        self.actualizar_interfaz(highlight_prod_id=prod_id)
        return True

    def cambiar_cantidad_carrito(self, prod_id: int, delta: int):
        # Buscar el item en carrito
        item = next((c for c in self.carrito if c["producto"].idProducto == prod_id), None)
        if not item:
            return

        nueva_cantidad = item["cantidad"] + delta
        if nueva_cantidad <= 0:
            self.eliminar_del_carrito(prod_id)
            return

        stock_disponible = self.stock_db.get(prod_id, 0)
        if nueva_cantidad > stock_disponible:
            QMessageBox.warning(self.view, "Stock Insuficiente", f"No puedes exceder el stock disponible de {stock_disponible} unidades.")
            return

        item["cantidad"] = nueva_cantidad
        self.actualizar_interfaz()

    def actualizar_interfaz(self, highlight_prod_id=None):
        if highlight_prod_id is not None:
            self.highlighted_prod_id = highlight_prod_id

        self.view.cart_table.setRowCount(0)
        
        total = 0.0
        carrito_ids = []

        for item in self.carrito:
            prod = item["producto"]
            cant = item["cantidad"]
            precio = float(prod.precioLista)
            subtotal = precio * cant
            total += subtotal
            carrito_ids.append(prod.idProducto)

            row = self.view.cart_table.rowCount()
            self.view.cart_table.insertRow(row)

            # Verificar si se debe resaltar esta fila (sutil fondo azul)
            es_resaltado = (prod.idProducto == self.highlighted_prod_id)
            bg_color = "#1a3e5c" if es_resaltado else "#121212"
            brush = QBrush(QColor(bg_color))

            # Código (ID) centrado
            id_item = QTableWidgetItem(str(prod.idProducto))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setBackground(brush)
            self.view.cart_table.setItem(row, 0, id_item)

            # Nombre Producto
            nombre_item = QTableWidgetItem(prod.nombre)
            nombre_item.setFlags(nombre_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            nombre_item.setBackground(brush)
            self.view.cart_table.setItem(row, 1, nombre_item)

            # Cantidad Widget (alineado a la derecha en QuantityWidget)
            qty_widget = QuantityWidget(
                quantity=cant,
                on_increment=lambda checked=False, pid=prod.idProducto: self.cambiar_cantidad_carrito(pid, 1),
                on_decrement=lambda checked=False, pid=prod.idProducto: self.cambiar_cantidad_carrito(pid, -1)
            )
            qty_widget.setStyleSheet(f"background-color: {bg_color};")
            self.view.cart_table.setCellWidget(row, 2, qty_widget)

            # Precio (alineado a la derecha)
            precio_item = QTableWidgetItem(f"${precio:.2f}")
            precio_item.setFlags(precio_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            precio_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            precio_item.setBackground(brush)
            self.view.cart_table.setItem(row, 3, precio_item)

            # Subtotal (alineado a la derecha)
            subtotal_item = QTableWidgetItem(f"${subtotal:.2f}")
            subtotal_item.setFlags(subtotal_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            subtotal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            subtotal_item.setBackground(brush)
            self.view.cart_table.setItem(row, 4, subtotal_item)
            
            # Botón eliminar con ícono de papelera únicamente
            btn_eliminar = QPushButton("🗑")
            btn_eliminar.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #d9534f;
                    font-size: 16px;
                    border: none;
                }
                QPushButton:hover {
                    color: #c9302c;
                }
            """)
            btn_eliminar.clicked.connect(lambda checked=False, pid=prod.idProducto: self.eliminar_del_carrito(pid))
            
            widget_eliminar = QWidget()
            widget_eliminar.setStyleSheet(f"background-color: {bg_color};")
            layout_eliminar = QHBoxLayout(widget_eliminar)
            layout_eliminar.setContentsMargins(5, 2, 5, 2)
            layout_eliminar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_eliminar.addWidget(btn_eliminar)
            self.view.cart_table.setCellWidget(row, 5, widget_eliminar)

        self.view.lbl_total.setText(f"$ {total:.2f}")
        self.actualizar_sugerencias(carrito_ids)

        # Iniciar timer para remover el resaltado de la fila a los 1000ms
        if self.highlighted_prod_id is not None:
            QTimer.singleShot(1000, self._remover_resaltado)

    def _remover_resaltado(self):
        self.highlighted_prod_id = None
        self.actualizar_interfaz()
        
    def eliminar_del_carrito(self, prod_id):
        item = next((i for i in self.carrito if i["producto"].idProducto == prod_id), None)
        if not item:
            return
        prod = item["producto"]
        
        reply = QMessageBox.question(
            self.view,
            "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar '{prod.nombre}' del carrito?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.carrito = [i for i in self.carrito if i["producto"].idProducto != prod_id]
            self.actualizar_interfaz()
            NotificationToast(self.view.window(), f"✓ Producto eliminado: {prod.nombre}")

    def actualizar_sugerencias(self, carrito_ids):
        # Limpiar completamente el layout (incluyendo widgets y espaciadores/stretches)
        while self.view.suggestions_layout.count():
            item = self.view.suggestions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                if widget not in (self.view.lbl_no_suggestions, self.view.lbl_sug_subtitle):
                    widget.deleteLater()

        self.view.suggestions_layout.addWidget(self.view.lbl_sug_subtitle)

        if not carrito_ids:
            self.view.suggestions_layout.addWidget(self.view.lbl_no_suggestions)
            return

        recomendados = MineriaService.sugerir_venta_cruzada(carrito_ids)

        if not recomendados:
            lbl = QLabel("Sin sugerencias asociadas para estos productos.")
            lbl.setStyleSheet("color: #a0a0a0; font-style: italic; font-size: 14px;")
            self.view.suggestions_layout.addWidget(lbl)
            return

        for prod_id, confianza in recomendados:
            if prod_id in self.productos_db:
                prod = self.productos_db[prod_id]
                rec_card = QWidget()
                rec_card.setStyleSheet("QWidget { background-color: #252525; border: 1px solid #3a3a3a; border-radius: 6px; }")
                layout = QHBoxLayout(rec_card)
                layout.setContentsMargins(10, 8, 10, 8)
                
                # Layout vertical para los textos descriptivos
                text_widget = QWidget()
                text_widget.setStyleSheet("border: none; background: transparent;")
                text_layout = QVBoxLayout(text_widget)
                text_layout.setContentsMargins(0, 0, 0, 0)
                text_layout.setSpacing(2)
                
                text_lbl = QLabel(f"<b>{prod.nombre}</b><br><font color='#2a82da'>${prod.precioLista:.2f}</font>")
                text_lbl.setStyleSheet("color: #ffffff; font-size: 14px; border: none; background: transparent;")
                
                # Indicador de porcentaje cálido sutil en cursiva de 14px
                pct_conf = int(confianza * 100)
                lbl_conf = QLabel(f"🔥 Confianza: {pct_conf}%")
                lbl_conf.setStyleSheet("color: #d1b894; font-size: 14px; font-style: italic; border: none; background: transparent;")
                lbl_conf.setToolTip(f"El {pct_conf}% de los clientes que compraron este producto también llevaron este artículo.")
                
                text_layout.addWidget(text_lbl)
                text_layout.addWidget(lbl_conf)
                
                btn_add_rec = QPushButton(" + ")
                btn_add_rec.setStyleSheet("QPushButton { background-color: #2a82da; color: white; border: none; border-radius: 4px; font-weight: bold; padding: 4px 8px; } QPushButton:hover { background-color: #3b93eb; }")
                btn_add_rec.clicked.connect(lambda checked=False, pid=prod_id: self.seleccionar_sugerencia(pid))
                
                # Hacer la tarjeta clickeable para seleccionar sugerencia
                rec_card.mousePressEvent = lambda event, pid=prod_id: self.seleccionar_sugerencia(pid)
                
                layout.addWidget(text_widget, stretch=1)
                layout.addWidget(btn_add_rec)
                self.view.suggestions_layout.addWidget(rec_card)

        self.view.suggestions_layout.addStretch()

    def seleccionar_sugerencia(self, prod_id):
        prod = self.productos_db.get(prod_id)
        if not prod:
            return
            
        # Encontrar index de la categoría
        cat_index = 0
        for i in range(self.view.combo_categorias.count()):
            if self.view.combo_categorias.itemData(i) == prod.idCategoria:
                cat_index = i
                break
                
        # Cambiar categoría bloqueando señales
        self.view.combo_categorias.blockSignals(True)
        self.view.combo_categorias.setCurrentIndex(cat_index)
        self.view.combo_categorias.blockSignals(False)
        
        # Filtrar manualmente
        self._filtrar_productos_por_categoria()
        
        # Encontrar index del producto
        prod_index = -1
        for i in range(self.view.combo_productos.count()):
            if self.view.combo_productos.itemData(i) == prod_id:
                prod_index = i
                break
                
        if prod_index >= 0:
            self.view.combo_productos.blockSignals(True)
            self.view.combo_productos.setCurrentIndex(prod_index)
            self.view.combo_productos.blockSignals(False)
            
            # Sincronizar campos
            self._on_producto_combo_changed(prod_index)
            
        # Dar foco al spin_cantidad y seleccionar su contenido
        self.view.spin_cantidad.setFocus()
        self.view.spin_cantidad.selectAll()

    def limpiar_carrito(self):
        # Solicitar confirmación antes de vaciar el carrito
        reply = QMessageBox.question(
            self.view,
            "Confirmar acción",
            "¿Estás seguro de que deseas limpiar el carrito de compras?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.carrito.clear()
            self.actualizar_interfaz()
            NotificationToast(self.view.window(), "✓ Carrito de compras limpio")
        
    def procesar_venta(self):
        if not self.carrito:
            QMessageBox.warning(self.view, "Carrito Vacío", "No puedes procesar una venta vacía.")
            return
            
        id_cliente = self.view.combo_cliente.currentData()
        id_pago = self.view.combo_pago.currentData()
        
        if not id_pago:
            QMessageBox.warning(self.view, "Datos Faltantes", "Debes seleccionar un medio de pago válido.")
            return
            
        total = sum(float(item["producto"].precioLista) * item["cantidad"] for item in self.carrito)
        id_usuario = 1 # Usuario por defecto o logueado
        
        # Confirmar antes de procesar la venta
        reply = QMessageBox.question(
            self.view,
            "Confirmar venta",
            f"¿Estás seguro de que deseas procesar la venta por un total de ${total:.2f}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        db = SessionLocal()
        try:
            # Procesar transaccionalmente
            POSService.procesar_venta(
                session=db,
                id_usuario=id_usuario,
                carrito=self.carrito,
                total=total,
                id_medio_pago=id_pago,
                id_cliente=id_cliente
            )
            # Confirmar si todo salio bien
            db.commit()
            
            NotificationToast(self.view.window(), "✓ Venta procesada correctamente. Inventario actualizado.")
            
            # Refrescar stock en memoria y vaciar combos duplicados de manera limpia
            self._cargar_datos_maestros()
            self.limpiar_carrito_silencioso()
            self.limpiar_busqueda()
        except ValueError as ve:
            db.rollback()
            QMessageBox.warning(self.view, "Error de Validación", str(ve))
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self.view, "Error en Transacción", f"No se pudo procesar la venta: {str(e)}")
        finally:
            db.close()

    def limpiar_carrito_silencioso(self):
        self.carrito.clear()
        self.actualizar_interfaz()
