import re
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QTableWidgetItem, QMessageBox
from views.actores_view import ActoresView
from views.notification_toast import NotificationToast
from utils.signals import global_signals
from config.db import SessionLocal
from models.actores import Cliente, Proveedor
from sqlalchemy.exc import IntegrityError

class ActoresController(QObject):
    def __init__(self):
        super().__init__()
        self.view = ActoresView()
        
        # Estado de edición
        self.editando_cliente_id = None  # Contiene el idCliente si estamos editando cliente
        self.editando_proveedor_id = None # Contiene el idProveedor si estamos editando proveedor
        
        # Conectar eventos de clientes
        self.view.btn_guardar_cliente.clicked.connect(self.guardar_cliente)
        self.view.btn_limpiar_cliente.clicked.connect(self.limpiar_formulario_cliente)
        self.view.btn_editar_cliente.clicked.connect(self.preparar_edicion_cliente)
        self.view.btn_eliminar_cliente.clicked.connect(self.eliminar_cliente)
        self.view.txt_buscar_cliente.textChanged.connect(self.filtrar_clientes)
        self.view.txt_num_doc_cliente.textChanged.connect(self.validar_live_cliente_doc)
        self.view.cmb_tipo_doc_cliente.currentIndexChanged.connect(lambda: self.validar_live_cliente_doc(self.view.txt_num_doc_cliente.text()))
        self.view.txt_cliente_correo.textChanged.connect(self.validar_live_cliente_correo)
        self.view.tabla_clientes.doubleClicked.connect(lambda index: self.preparar_edicion_cliente())
        
        # Conectar eventos de proveedores
        self.view.btn_guardar_proveedor.clicked.connect(self.guardar_proveedor)
        self.view.btn_limpiar_proveedor.clicked.connect(self.limpiar_formulario_proveedor)
        self.view.btn_editar_proveedor.clicked.connect(self.preparar_edicion_proveedor)
        self.view.btn_eliminar_proveedor.clicked.connect(self.eliminar_proveedor)
        self.view.txt_buscar_proveedor.textChanged.connect(self.filtrar_proveedores)
        self.view.txt_num_doc_proveedor.textChanged.connect(self.validar_live_proveedor_doc)
        self.view.cmb_tipo_doc_proveedor.currentIndexChanged.connect(lambda: self.validar_live_proveedor_doc(self.view.txt_num_doc_proveedor.text()))
        self.view.txt_proveedor_correo.textChanged.connect(self.validar_live_proveedor_correo)
        self.view.tabla_proveedores.doubleClicked.connect(lambda index: self.preparar_edicion_proveedor())
        
    def start(self):
        # Cargar datos iniciales
        self.cargar_clientes()
        self.cargar_proveedores()
        
    def cargar_clientes(self):
        self.view.tabla_clientes.setSortingEnabled(False)
        self.view.tabla_clientes.setRowCount(0)
        
        db = SessionLocal()
        try:
            clientes = db.query(Cliente).all()
            for cli in clientes:
                row = self.view.tabla_clientes.rowCount()
                self.view.tabla_clientes.insertRow(row)
                
                item_id = QTableWidgetItem(str(cli.idCliente))
                item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.view.tabla_clientes.setItem(row, 0, item_id)
                
                self.view.tabla_clientes.setItem(row, 1, QTableWidgetItem(cli.tipoDocumento or ""))
                self.view.tabla_clientes.setItem(row, 2, QTableWidgetItem(cli.numeroDocumento or ""))
                self.view.tabla_clientes.setItem(row, 3, QTableWidgetItem(cli.nombres or ""))
                self.view.tabla_clientes.setItem(row, 4, QTableWidgetItem(cli.apellidos or ""))
                self.view.tabla_clientes.setItem(row, 5, QTableWidgetItem(cli.telefono or ""))
                self.view.tabla_clientes.setItem(row, 6, QTableWidgetItem(cli.correoElectronico or ""))
        except Exception as e:
            print(f"Error al cargar clientes: {e}")
        finally:
            db.close()
            
        self.view.tabla_clientes.setSortingEnabled(True)
        self.filtrar_clientes() # Re-aplicar filtro si hay texto escrito
        
    def cargar_proveedores(self):
        self.view.tabla_proveedores.setSortingEnabled(False)
        self.view.tabla_proveedores.setRowCount(0)
        
        db = SessionLocal()
        try:
            proveedores = db.query(Proveedor).all()
            for prov in proveedores:
                row = self.view.tabla_proveedores.rowCount()
                self.view.tabla_proveedores.insertRow(row)
                
                item_id = QTableWidgetItem(str(prov.idProveedor))
                item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.view.tabla_proveedores.setItem(row, 0, item_id)
                
                self.view.tabla_proveedores.setItem(row, 1, QTableWidgetItem(prov.tipoDocumento or ""))
                self.view.tabla_proveedores.setItem(row, 2, QTableWidgetItem(prov.numeroDocumento or ""))
                self.view.tabla_proveedores.setItem(row, 3, QTableWidgetItem(prov.nombreRazonSocial))
                self.view.tabla_proveedores.setItem(row, 4, QTableWidgetItem(prov.telefono or ""))
                self.view.tabla_proveedores.setItem(row, 5, QTableWidgetItem(prov.direccion or ""))
                self.view.tabla_proveedores.setItem(row, 6, QTableWidgetItem(prov.correoElectronico or ""))
        except Exception as e:
            print(f"Error al cargar proveedores: {e}")
        finally:
            db.close()
            
        self.view.tabla_proveedores.setSortingEnabled(True)
        self.filtrar_proveedores() # Re-aplicar filtro
        
    # --- FLUX DE ESTADOS CENTRALIZADO ---
    
    def set_form_state_cliente(self, state, cli=None):
        if state == "CREATE":
            self.editando_cliente_id = None
            self.view.txt_num_doc_cliente.clear()
            self.view.txt_num_doc_cliente.setEnabled(True)
            self.view.txt_num_doc_cliente.setStyleSheet("")
            self.view.cmb_tipo_doc_cliente.setCurrentIndex(0)
            self.view.cmb_tipo_doc_cliente.setEnabled(True)
            self.view.txt_cliente_nombres.clear()
            self.view.txt_cliente_apellidos.clear()
            self.view.txt_cliente_telefono.clear()
            self.view.txt_cliente_correo.clear()
            self.view.txt_cliente_correo.setStyleSheet("")
            self.view.lbl_titulo_form_cliente.setText("Nuevo Cliente")
            self.view.btn_guardar_cliente.setText("Guardar")
        elif state == "EDIT" and cli:
            self.editando_cliente_id = cli.idCliente
            self.view.txt_num_doc_cliente.setText(cli.numeroDocumento or "")
            self.view.txt_num_doc_cliente.setEnabled(False)
            self.view.txt_num_doc_cliente.setStyleSheet("")
            idx = self.view.cmb_tipo_doc_cliente.findText(cli.tipoDocumento or "DNI")
            if idx >= 0:
                self.view.cmb_tipo_doc_cliente.setCurrentIndex(idx)
            self.view.cmb_tipo_doc_cliente.setEnabled(False)
            self.view.txt_cliente_nombres.setText(cli.nombres or "")
            self.view.txt_cliente_apellidos.setText(cli.apellidos or "")
            self.view.txt_cliente_telefono.setText(cli.telefono or "")
            self.view.txt_cliente_correo.setText(cli.correoElectronico or "")
            self.view.txt_cliente_correo.setStyleSheet("")
            self.view.lbl_titulo_form_cliente.setText(f"Editar Cliente [{cli.idCliente}]")
            self.view.btn_guardar_cliente.setText("Actualizar")

    def set_form_state_proveedor(self, state, prov=None):
        if state == "CREATE":
            self.editando_proveedor_id = None
            self.view.txt_num_doc_proveedor.clear()
            self.view.txt_num_doc_proveedor.setEnabled(True)
            self.view.txt_num_doc_proveedor.setStyleSheet("")
            self.view.cmb_tipo_doc_proveedor.setCurrentIndex(0)
            self.view.cmb_tipo_doc_proveedor.setEnabled(True)
            self.view.txt_proveedor_nombre.clear()
            self.view.txt_proveedor_telefono.clear()
            self.view.txt_proveedor_direccion.clear()
            self.view.txt_proveedor_correo.clear()
            self.view.txt_proveedor_correo.setStyleSheet("")
            self.view.lbl_titulo_form_proveedor.setText("Nuevo Proveedor")
            self.view.btn_guardar_proveedor.setText("Guardar")
        elif state == "EDIT" and prov:
            self.editando_proveedor_id = prov.idProveedor
            self.view.txt_num_doc_proveedor.setText(prov.numeroDocumento or "")
            self.view.txt_num_doc_proveedor.setEnabled(False)
            self.view.txt_num_doc_proveedor.setStyleSheet("")
            idx = self.view.cmb_tipo_doc_proveedor.findText(prov.tipoDocumento or "RUC")
            if idx >= 0:
                self.view.cmb_tipo_doc_proveedor.setCurrentIndex(idx)
            self.view.cmb_tipo_doc_proveedor.setEnabled(False)
            self.view.txt_proveedor_nombre.setText(prov.nombreRazonSocial or "")
            self.view.txt_proveedor_telefono.setText(prov.telefono or "")
            self.view.txt_proveedor_direccion.setText(prov.direccion or "")
            self.view.txt_proveedor_correo.setText(prov.correoElectronico or "")
            self.view.txt_proveedor_correo.setStyleSheet("")
            self.view.lbl_titulo_form_proveedor.setText(f"Editar Proveedor [{prov.idProveedor}]")
            self.view.btn_guardar_proveedor.setText("Actualizar")

    # --- FILTRADO POLIMÓRFICO ---
    
    def filtrar_clientes(self):
        busqueda = self.view.txt_buscar_cliente.text().strip().lower()
        for r in range(self.view.tabla_clientes.rowCount()):
            self.view.tabla_clientes.setRowHidden(r, False)
            item_id = self.view.tabla_clientes.item(r, 0)
            item_nombre = self.view.tabla_clientes.item(r, 1)
            
            if not item_id or not item_nombre:
                continue
                
            match = (busqueda in item_id.text().lower()) or (busqueda in item_nombre.text().lower())
            if not match:
                self.view.tabla_clientes.setRowHidden(r, True)
                
    def filtrar_proveedores(self):
        busqueda = self.view.txt_buscar_proveedor.text().strip().lower()
        for r in range(self.view.tabla_proveedores.rowCount()):
            self.view.tabla_proveedores.setRowHidden(r, False)
            item_id = self.view.tabla_proveedores.item(r, 0)
            item_nombre = self.view.tabla_proveedores.item(r, 1)
            
            if not item_id or not item_nombre:
                continue
                
            match = (busqueda in item_id.text().lower()) or (busqueda in item_nombre.text().lower())
            if not match:
                self.view.tabla_proveedores.setRowHidden(r, True)

    # --- LIVE VALIDATION ---
    
    def validar_live_cliente_doc(self, text):
        text = text.strip()
        tipo_doc = self.view.cmb_tipo_doc_cliente.currentText()
        if not text:
            self.view.txt_num_doc_cliente.setStyleSheet("")
            return True
        
        valid = False
        if tipo_doc == "DNI":
            valid = bool(re.match(r"^\d{8}$", text))
        elif tipo_doc == "CE":
            valid = bool(re.match(r"^\d{9}$", text))
        elif tipo_doc == "RUC":
            valid = bool(re.match(r"^\d{11}$", text))
        else:
            valid = bool(len(text) >= 5)
            
        if valid:
            self.view.txt_num_doc_cliente.setStyleSheet("")
            return True
        else:
            self.view.txt_num_doc_cliente.setStyleSheet("border: 1px solid #c62828; background-color: #2d2d2d; color: #ffffff;")
            return False

    def validar_live_cliente_correo(self, text):
        text = text.strip()
        if not text:
            self.view.txt_cliente_correo.setStyleSheet("")
            return True
        if re.match(r"^[^@]+@[^@]+\.[^@]+$", text):
            self.view.txt_cliente_correo.setStyleSheet("")
            return True
        else:
            self.view.txt_cliente_correo.setStyleSheet("border: 1px solid #c62828; background-color: #2d2d2d; color: #ffffff;")
            return False

    def validar_live_proveedor_doc(self, text):
        text = text.strip()
        tipo_doc = self.view.cmb_tipo_doc_proveedor.currentText()
        if not text:
            self.view.txt_num_doc_proveedor.setStyleSheet("")
            return True
        
        valid = False
        if tipo_doc == "RUC":
            valid = bool(re.match(r"^\d{11}$", text))
        else:
            valid = bool(re.match(r"^\d{11}$", text))
            
        if valid:
            self.view.txt_num_doc_proveedor.setStyleSheet("")
            return True
        else:
            self.view.txt_num_doc_proveedor.setStyleSheet("border: 1px solid #c62828; background-color: #2d2d2d; color: #ffffff;")
            return False

    def validar_live_proveedor_correo(self, text):
        text = text.strip()
        if not text:
            self.view.txt_proveedor_correo.setStyleSheet("")
            return True
        if re.match(r"^[^@]+@[^@]+\.[^@]+$", text):
            self.view.txt_proveedor_correo.setStyleSheet("")
            return True
        else:
            self.view.txt_proveedor_correo.setStyleSheet("border: 1px solid #c62828; background-color: #2d2d2d; color: #ffffff;")
            return False



    # --- LÓGICA CLIENTES ---
    
    def limpiar_formulario_cliente(self):
        self.set_form_state_cliente("CREATE")
        
    def preparar_edicion_cliente(self):
        selected_ranges = self.view.tabla_clientes.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self.view, "Selección requerida", "Por favor, seleccione un cliente de la tabla.")
            return
            
        row = selected_ranges[0].topRow()
        item_id = self.view.tabla_clientes.item(row, 0)
        if not item_id:
            return
            
        try:
            cliente_id = int(item_id.text())
        except ValueError:
            return
            
        db = SessionLocal()
        try:
            cli = db.query(Cliente).filter(Cliente.idCliente == cliente_id).first()
            if cli:
                self.set_form_state_cliente("EDIT", cli)
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"No se pudo cargar los datos del cliente: {e}")
        finally:
            db.close()

    def guardar_cliente(self):
        # Validaciones de entrada
        tipo_doc = self.view.cmb_tipo_doc_cliente.currentText()
        num_doc = self.view.txt_num_doc_cliente.text().strip()
        nombres = self.view.txt_cliente_nombres.text().strip()
        apellidos = self.view.txt_cliente_apellidos.text().strip()
        telefono = self.view.txt_cliente_telefono.text().strip() or None
        correo = self.view.txt_cliente_correo.text().strip() or None
        
        if not num_doc:
            QMessageBox.warning(self.view, "Campo requerido", "El campo Número de Documento es obligatorio.")
            return
        if not nombres or not apellidos:
            QMessageBox.warning(self.view, "Campo requerido", "Los campos Nombres y Apellidos son obligatorios.")
            return
            
        # Validación de formato de campos
        if not self.validar_live_cliente_doc(num_doc):
            QMessageBox.warning(self.view, "Documento inválido", "El formato del documento no es válido para el tipo seleccionado.")
            return
        if correo and not self.validar_live_cliente_correo(correo):
            QMessageBox.warning(self.view, "Correo inválido", "El formato del correo electrónico es incorrecto.")
            return
            
        db = SessionLocal()
        try:
            if self.editando_cliente_id is None:
                # MODO CREACIÓN: Poka-yoke preventivo
                existente = db.query(Cliente).filter(Cliente.numeroDocumento == num_doc).first()
                if existente:
                    reply = QMessageBox.warning(
                        self.view,
                        "Documento Duplicado",
                        f"El cliente con Documento '{num_doc}' ya está registrado.\n¿Desea limpiar el formulario?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Cancel
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.limpiar_formulario_cliente()
                    return
                    
                nuevo_cliente = Cliente(
                    tipoDocumento=tipo_doc,
                    numeroDocumento=num_doc,
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                    correoElectronico=correo
                )
                db.add(nuevo_cliente)
                db.commit()
                NotificationToast(self.view.window(), "✓ Cliente guardado exitosamente.")
            else:
                # MODO EDICIÓN: db.merge() para resiliencia concurrente
                cliente_a_actualizar = Cliente(
                    idCliente=self.editando_cliente_id,
                    tipoDocumento=tipo_doc,
                    numeroDocumento=num_doc,
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                    correoElectronico=correo
                )
                db.merge(cliente_a_actualizar)
                db.commit()
                NotificationToast(self.view.window(), "✓ Cliente actualizado exitosamente.")
                    
            self.limpiar_formulario_cliente()
            self.cargar_clientes()
            global_signals.cliente_actualizado.emit()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self.view, "Error al guardar", f"Ocurrió un error al procesar la operación:\n{str(e)}")
        finally:
            db.close()
            
    def eliminar_cliente(self):
        selected_ranges = self.view.tabla_clientes.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self.view, "Selección requerida", "Por favor, seleccione un cliente de la tabla.")
            return
            
        row = selected_ranges[0].topRow()
        item_id = self.view.tabla_clientes.item(row, 0)
        item_nombre = self.view.tabla_clientes.item(row, 1)
        if not item_id:
            return
            
        try:
            cliente_id = int(item_id.text())
        except ValueError:
            return
            
        nombre = item_nombre.text() if item_nombre else str(cliente_id)
        
        reply = QMessageBox.question(
            self.view,
            "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar al cliente '{nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        db = SessionLocal()
        try:
            cli = db.query(Cliente).filter(Cliente.idCliente == cliente_id).first()
            if cli:
                db.delete(cli)
                db.commit()
                NotificationToast(self.view.window(), f"✓ Cliente '{nombre}' eliminado.")
                self.cargar_clientes()
                # Si estábamos editando este cliente, limpiar el formulario
                if self.editando_cliente_id == cliente_id:
                    self.limpiar_formulario_cliente()
            else:
                QMessageBox.warning(self.view, "Error", "El cliente ya no existe en la base de datos.")
        except IntegrityError:
            db.rollback()
            QMessageBox.warning(self.view, "Restricción de Integridad", "No se puede eliminar este cliente porque tiene transacciones de ventas registradas.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self.view, "Error", f"Ocurrió un error al eliminar:\n{e}")
        finally:
            db.close()

    # --- LÓGICA PROVEEDORES ---
    
    def limpiar_formulario_proveedor(self):
        self.set_form_state_proveedor("CREATE")
        
    def preparar_edicion_proveedor(self):
        selected_ranges = self.view.tabla_proveedores.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self.view, "Selección requerida", "Por favor, seleccione un proveedor de la tabla.")
            return
            
        row = selected_ranges[0].topRow()
        item_id = self.view.tabla_proveedores.item(row, 0)
        if not item_id:
            return
            
        try:
            proveedor_id = int(item_id.text())
        except ValueError:
            return
            
        db = SessionLocal()
        try:
            prov = db.query(Proveedor).filter(Proveedor.idProveedor == proveedor_id).first()
            if prov:
                self.set_form_state_proveedor("EDIT", prov)
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"No se pudo cargar los datos del proveedor: {e}")
        finally:
            db.close()

    def guardar_proveedor(self):
        # Validaciones de entrada
        tipo_doc = self.view.cmb_tipo_doc_proveedor.currentText()
        num_doc = self.view.txt_num_doc_proveedor.text().strip()
        nombre = self.view.txt_proveedor_nombre.text().strip()
        telefono = self.view.txt_proveedor_telefono.text().strip() or None
        direccion = self.view.txt_proveedor_direccion.text().strip() or None
        correo = self.view.txt_proveedor_correo.text().strip() or None
        
        if not num_doc:
            QMessageBox.warning(self.view, "Campo requerido", "El campo Número de Documento es obligatorio.")
            return
        if not nombre:
            QMessageBox.warning(self.view, "Campo requerido", "El campo Razón Social es obligatorio.")
            return
            
        # Validar formatos
        if not self.validar_live_proveedor_doc(num_doc):
            QMessageBox.warning(self.view, "Documento inválido", "El formato del documento no es válido.")
            return
        if correo and not self.validar_live_proveedor_correo(correo):
            QMessageBox.warning(self.view, "Correo inválido", "El formato del correo electrónico es incorrecto.")
            return
            
        db = SessionLocal()
        try:
            if self.editando_proveedor_id is None:
                # MODO CREACIÓN: Poka-yoke preventivo
                existente = db.query(Proveedor).filter(Proveedor.numeroDocumento == num_doc).first()
                if existente:
                    reply = QMessageBox.warning(
                        self.view,
                        "Documento Duplicado",
                        f"El proveedor con Documento '{num_doc}' ya está registrado.\n¿Desea limpiar el formulario?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Cancel
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.limpiar_formulario_proveedor()
                    return
                    
                nuevo_prov = Proveedor(
                    tipoDocumento=tipo_doc,
                    numeroDocumento=num_doc,
                    nombreRazonSocial=nombre,
                    telefono=telefono,
                    direccion=direccion,
                    correoElectronico=correo
                )
                db.add(nuevo_prov)
                db.commit()
                NotificationToast(self.view.window(), "✓ Proveedor guardado exitosamente.")
            else:
                # MODO EDICIÓN: db.merge() para resiliencia concurrente
                proveedor_a_actualizar = Proveedor(
                    idProveedor=self.editando_proveedor_id,
                    tipoDocumento=tipo_doc,
                    numeroDocumento=num_doc,
                    nombreRazonSocial=nombre,
                    telefono=telefono,
                    direccion=direccion,
                    correoElectronico=correo
                )
                db.merge(proveedor_a_actualizar)
                db.commit()
                NotificationToast(self.view.window(), "✓ Proveedor actualizado exitosamente.")
                    
            self.limpiar_formulario_proveedor()
            self.cargar_proveedores()
            global_signals.proveedor_actualizado.emit()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self.view, "Error al guardar", f"Ocurrió un error al procesar la operación:\n{str(e)}")
        finally:
            db.close()
            
    def eliminar_proveedor(self):
        selected_ranges = self.view.tabla_proveedores.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self.view, "Selección requerida", "Por favor, seleccione un proveedor de la tabla.")
            return
            
        row = selected_ranges[0].topRow()
        item_id = self.view.tabla_proveedores.item(row, 0)
        item_nombre = self.view.tabla_proveedores.item(row, 1)
        if not item_id:
            return
            
        try:
            proveedor_id = int(item_id.text())
        except ValueError:
            return
            
        nombre = item_nombre.text() if item_nombre else str(proveedor_id)
        
        reply = QMessageBox.question(
            self.view,
            "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar al proveedor '{nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        db = SessionLocal()
        try:
            prov = db.query(Proveedor).filter(Proveedor.idProveedor == proveedor_id).first()
            if prov:
                db.delete(prov)
                db.commit()
                NotificationToast(self.view.window(), f"✓ Proveedor '{nombre}' eliminado.")
                self.cargar_proveedores()
                # Si estábamos editando este proveedor, limpiar el formulario
                if self.editando_proveedor_id == proveedor_id:
                    self.limpiar_formulario_proveedor()
            else:
                QMessageBox.warning(self.view, "Error", "El proveedor ya no existe en la base de datos.")
        except IntegrityError:
            db.rollback()
            QMessageBox.warning(self.view, "Restricción de Integridad", "No se puede eliminar este proveedor porque tiene transacciones de compras registradas.")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self.view, "Error", f"Ocurrió un error al eliminar:\n{e}")
        finally:
            db.close()
