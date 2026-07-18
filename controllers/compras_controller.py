from PySide6.QtCore import QObject, Qt, QEvent
from PySide6.QtWidgets import QCompleter, QPushButton, QSpinBox, QDoubleSpinBox, QTableWidgetItem
import datetime
from decimal import Decimal

from config.db import SessionLocal
from models.actores import Proveedor
from models.catalogo import Producto
from models.suministro import Compra, DetalleCompra, Inventario
from views.compras_view import ComprasView
from views.notification_toast import NotificationToast

class ComprasController(QObject):
    def __init__(self):
        super().__init__()
        self.view = ComprasView()
        self.productos_data = {}  # { 'texto_completer': idProducto }
        self.proveedores_data = {} # { 'texto_completer': idProveedor }
        self.init_connections()
        self.cargar_datos_iniciales()

    def init_connections(self):
        # Flujo teclado (Enter -> Cantidad -> Enter -> Buscar)
        self.view.line_buscar.returnPressed.connect(self.agregar_producto_desde_buscador)
        self.view.btn_emitir.clicked.connect(self.emitir_compra)
        self.view.btn_limpiar.clicked.connect(self.limpiar_formulario)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if isinstance(obj, (QSpinBox, QDoubleSpinBox)):
                    self.view.line_buscar.setFocus()
                    return True # Evento consumido
        return super().eventFilter(obj, event)

    def cargar_datos_iniciales(self):
        self.productos_data.clear()
        self.proveedores_data.clear()
        self.view.combo_proveedor.clear()

        with SessionLocal() as db:
            # 1. Cargar Proveedores
            proveedores = db.query(Proveedor).all()
            lista_proveedores = []
            for p in proveedores:
                texto = f"{p.idProveedor} - {p.nombreRazonSocial}"
                self.proveedores_data[texto] = p.idProveedor
                lista_proveedores.append(texto)
            
            completer_prov = QCompleter(lista_proveedores)
            completer_prov.setFilterMode(Qt.MatchContains)
            completer_prov.setCaseSensitivity(Qt.CaseInsensitive)
            self.view.combo_proveedor.setCompleter(completer_prov)
            self.view.combo_proveedor.addItems([""] + lista_proveedores)

            # 2. Cargar Productos (con estado stock)
            productos = db.query(Producto).all()
            lista_productos = []
            
            for p in productos:
                inv = db.query(Inventario).filter(Inventario.idProducto == p.idProducto).first()
                stock = inv.cantidadDisponible if inv else 0
                
                if stock <= 5:
                    prefix = "[🔴 CRÍTICO]"
                elif stock <= 15:
                    prefix = "[🟡 BAJO]"
                else:
                    prefix = "[🟢 ÓPTIMO]"
                
                texto = f"{prefix} {p.idProducto} - {p.nombre}"
                self.productos_data[texto] = p.idProducto
                
                if stock <= 15:
                    lista_productos.insert(0, texto)
                else:
                    lista_productos.append(texto)

            completer_prod = QCompleter(lista_productos)
            completer_prod.setFilterMode(Qt.MatchContains)
            completer_prod.setCaseSensitivity(Qt.CaseInsensitive)
            self.view.line_buscar.setCompleter(completer_prod)

    def agregar_producto_desde_buscador(self):
        texto = self.view.line_buscar.text().strip()
        if not texto or texto not in self.productos_data:
            return
        
        id_prod = self.productos_data[texto]
        
        with SessionLocal() as db:
            prod = db.query(Producto).filter(Producto.idProducto == id_prod).first()
            if prod:
                # Obtener stock
                inv = db.query(Inventario).filter(Inventario.idProducto == id_prod).first()
                stock_actual = inv.cantidadDisponible if inv else 0
                
                if stock_actual <= 5:
                    # Mostrar alerta discreta si stock es muy bajo
                    NotificationToast(self.view.window(), f"⚠ Stock crítico ({stock_actual}) para '{prod.nombre}'.")
                
                self.agregar_fila_carrito(prod, stock_actual)
        
        self.view.line_buscar.clear()

    def agregar_fila_carrito(self, producto, stock_actual):
        row = self.view.tabla_detalle.rowCount()
        self.view.tabla_detalle.insertRow(row)

        # 0: Código
        item_cod = QTableWidgetItem(str(producto.idProducto))
        item_cod.setFlags(item_cod.flags() & ~Qt.ItemIsEditable)
        self.view.tabla_detalle.setItem(row, 0, item_cod)

        # 1: Nombre
        item_nom = QTableWidgetItem(producto.nombre)
        item_nom.setFlags(item_nom.flags() & ~Qt.ItemIsEditable)
        self.view.tabla_detalle.setItem(row, 1, item_nom)

        # 2: Stock Actual
        item_stock = QTableWidgetItem(str(stock_actual))
        item_stock.setFlags(item_stock.flags() & ~Qt.ItemIsEditable)
        item_stock.setTextAlignment(Qt.AlignCenter)
        self.view.tabla_detalle.setItem(row, 2, item_stock)

        # 3: Cantidad
        spin_cant = QSpinBox()
        spin_cant.setRange(1, 10000)
        spin_cant.setValue(1)
        spin_cant.valueChanged.connect(self.on_spin_changed)
        spin_cant.installEventFilter(self)
        self.view.tabla_detalle.setCellWidget(row, 3, spin_cant)

        # 4: Costo Unitario
        spin_costo = QDoubleSpinBox()
        spin_costo.setRange(0.01, 99999.99)
        spin_costo.setDecimals(2)
        spin_costo.setValue(float(producto.costoProducto))
        spin_costo.valueChanged.connect(self.on_spin_changed)
        spin_costo.installEventFilter(self)
        self.view.tabla_detalle.setCellWidget(row, 4, spin_costo)

        # 5: Subtotal
        item_sub = QTableWidgetItem(f"${spin_costo.value():.2f}")
        item_sub.setFlags(item_sub.flags() & ~Qt.ItemIsEditable)
        self.view.tabla_detalle.setItem(row, 5, item_sub)

        # 6: Acciones
        btn_del = QPushButton("❌")
        btn_del.clicked.connect(self.eliminar_fila_dinamica)
        self.view.tabla_detalle.setCellWidget(row, 6, btn_del)

        item_cod.setData(Qt.UserRole, producto.idProducto)
        self.recalcular_totales()

        # Foco a la cantidad y seleccionar el '1' para escribir directo
        spin_cant.setFocus()
        spin_cant.selectAll()

    def on_spin_changed(self, value=0):
        sender = self.sender()
        if sender:
            row = self.view.tabla_detalle.indexAt(sender.pos()).row()
            if row >= 0:
                self.recalcular_fila(row)

    def eliminar_fila_dinamica(self):
        sender = self.sender()
        if sender:
            row = self.view.tabla_detalle.indexAt(sender.pos()).row()
            if row >= 0:
                self.view.tabla_detalle.removeRow(row)
                self.recalcular_totales()

    def recalcular_fila(self, row):
        spin_cant = self.view.tabla_detalle.cellWidget(row, 3)
        spin_costo = self.view.tabla_detalle.cellWidget(row, 4)
        if not spin_cant or not spin_costo: return

        cant = spin_cant.value()
        costo = Decimal(str(spin_costo.value()))
        subtotal = Decimal(cant) * costo

        item_sub = self.view.tabla_detalle.item(row, 5)
        if item_sub:
            item_sub.setText(f"${subtotal:.2f}")

        self.recalcular_totales()

    def recalcular_totales(self):
        total = Decimal("0.00")
        for i in range(self.view.tabla_detalle.rowCount()):
            item_sub = self.view.tabla_detalle.item(i, 5)
            if item_sub:
                val_str = item_sub.text().replace("$", "")
                total += Decimal(val_str)
                
        self.view.lbl_total.setText(f"Total: ${total:.2f}")

    def emitir_compra(self):
        texto_prov = self.view.combo_proveedor.currentText()
        if texto_prov not in self.proveedores_data:
            NotificationToast(self.view.window(), "⚠ Seleccione un proveedor válido.")
            return

        id_proveedor = self.proveedores_data[texto_prov]
        row_count = self.view.tabla_detalle.rowCount()
        if row_count == 0:
            NotificationToast(self.view.window(), "⚠ El carrito de compras está vacío.")
            return

        factura = self.view.line_factura.text().strip()
        if not factura:
            now = datetime.datetime.now()
            factura = f"REQ-{now.strftime('%Y%m%d-%H%M')}"
            
        fecha_compra = self.view.date_fecha.date().toPython()
        total_str = self.view.lbl_total.text().replace("Total: $", "")
        monto_total = Decimal(total_str)

        with SessionLocal() as db:
            try:
                # 1. Compra
                nueva_compra = Compra(
                    idProveedor=id_proveedor,
                    idUsuario=1,
                    fechaCompra=fecha_compra,
                    montoTotal=monto_total
                )
                db.add(nueva_compra)
                db.flush()

                # 2. Detalles e Inventario
                for i in range(row_count):
                    id_producto = self.view.tabla_detalle.item(i, 0).data(Qt.UserRole)
                    cant = self.view.tabla_detalle.cellWidget(i, 3).value()
                    costo_str = self.view.tabla_detalle.cellWidget(i, 4).value()
                    costo = Decimal(str(costo_str))
                    subtotal = Decimal(cant) * costo

                    detalle = DetalleCompra(
                        idCompra=nueva_compra.idCompra,
                        idProducto=id_producto,
                        cantidad=cant,
                        costoUnitario=costo,
                        subtotal=subtotal
                    )
                    db.add(detalle)

                    inv = db.query(Inventario).filter(Inventario.idProducto == id_producto).first()
                    if inv:
                        inv.cantidadDisponible += cant
                        inv.fechaActualizacion = datetime.date.today()
                    else:
                        nuevo_inv = Inventario(
                            idProducto=id_producto,
                            fechaActualizacion=datetime.date.today(),
                            cantidadDisponible=cant
                        )
                        db.add(nuevo_inv)

                db.commit()
                NotificationToast(self.view.window(), f"✓ Compra {factura} emitida correctamente.")
                self.limpiar_formulario()
                self.cargar_datos_iniciales()

            except Exception as e:
                db.rollback()
                NotificationToast(self.view.window(), f"⚠ Error: {str(e)}")

    def limpiar_formulario(self):
        self.view.combo_proveedor.setCurrentIndex(0)
        self.view.line_factura.clear()
        self.view.date_fecha.setDate(datetime.date.today())
        self.view.tabla_detalle.setRowCount(0)
        self.recalcular_totales()
