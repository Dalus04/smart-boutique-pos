import re
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QTableWidgetItem, QMessageBox
from views.actores_view import ActoresView
from views.notification_toast import NotificationToast
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
        self.view.txt_cliente_id.textChanged.connect(self.validar_live_cliente_id)
        self.view.txt_cliente_correo.textChanged.connect(self.validar_live_cliente_correo)
        self.view.txt_cliente_id.editingFinished.connect(self.detectar_cliente_existente)
        self.view.tabla_clientes.doubleClicked.connect(lambda index: self.preparar_edicion_cliente())
        
        # Conectar eventos de proveedores
        self.view.btn_guardar_proveedor.clicked.connect(self.guardar_proveedor)
        self.view.btn_limpiar_proveedor.clicked.connect(self.limpiar_formulario_proveedor)
        self.view.btn_editar_proveedor.clicked.connect(self.preparar_edicion_proveedor)
        self.view.btn_eliminar_proveedor.clicked.connect(self.eliminar_proveedor)
        self.view.txt_buscar_proveedor.textChanged.connect(self.filtrar_proveedores)
        self.view.txt_proveedor_id.textChanged.connect(self.validar_live_proveedor_id)
        self.view.txt_proveedor_correo.textChanged.connect(self.validar_live_proveedor_correo)
        self.view.txt_proveedor_id.editingFinished.connect(self.detectar_proveedor_existente)
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
                
                self.view.tabla_clientes.setItem(row, 1, QTableWidgetItem(cli.nombresCompletos))
                self.view.tabla_clientes.setItem(row, 2, QTableWidgetItem(cli.telefono or ""))
                self.view.tabla_clientes.setItem(row, 3, QTableWidgetItem(cli.correoElectronico or ""))
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
                
                self.view.tabla_proveedores.setItem(row, 1, QTableWidgetItem(prov.nombreRazonSocial))
                self.view.tabla_proveedores.setItem(row, 2, QTableWidgetItem(prov.telefono or ""))
                self.view.tabla_proveedores.setItem(row, 3, QTableWidgetItem(prov.direccion or ""))
                self.view.tabla_proveedores.setItem(row, 4, QTableWidgetItem(prov.correoElectronico or ""))
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
            self.view.txt_cliente_id.clear()
            self.view.txt_cliente_id.setEnabled(True)
            self.view.txt_cliente_id.setStyleSheet("")
            self.view.txt_cliente_nombre.clear()
            self.view.txt_cliente_telefono.clear()
            self.view.txt_cliente_correo.clear()
            self.view.txt_cliente_correo.setStyleSheet("")
            self.view.lbl_titulo_form_cliente.setText("Nuevo Cliente")
            self.view.btn_guardar_cliente.setText("Guardar")
        elif state == "EDIT" and cli:
            self.editando_cliente_id = cli.idCliente
            self.view.txt_cliente_id.setText(str(cli.idCliente))
            self.view.txt_cliente_id.setEnabled(False)
            self.view.txt_cliente_id.setStyleSheet("")
            self.view.txt_cliente_nombre.setText(cli.nombresCompletos)
            self.view.txt_cliente_telefono.setText(cli.telefono or "")
            self.view.txt_cliente_correo.setText(cli.correoElectronico or "")
            self.view.txt_cliente_correo.setStyleSheet("")
            self.view.lbl_titulo_form_cliente.setText(f"Editar Cliente [{cli.idCliente}]")
            self.view.btn_guardar_cliente.setText("Actualizar")

    def set_form_state_proveedor(self, state, prov=None):
        if state == "CREATE":
            self.editando_proveedor_id = None
            self.view.txt_proveedor_id.clear()
            self.view.txt_proveedor_id.setEnabled(True)
            self.view.txt_proveedor_id.setStyleSheet("")
            self.view.txt_proveedor_nombre.clear()
            self.view.txt_proveedor_telefono.clear()
            self.view.txt_proveedor_direccion.clear()
            self.view.txt_proveedor_correo.clear()
            self.view.txt_proveedor_correo.setStyleSheet("")
            self.view.lbl_titulo_form_proveedor.setText("Nuevo Proveedor")
            self.view.btn_guardar_proveedor.setText("Guardar")
        elif state == "EDIT" and prov:
            self.editando_proveedor_id = prov.idProveedor
            self.view.txt_proveedor_id.setText(str(prov.idProveedor))
            self.view.txt_proveedor_id.setEnabled(False)
            self.view.txt_proveedor_id.setStyleSheet("")
            self.view.txt_proveedor_nombre.setText(prov.nombreRazonSocial)
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
    
    def validar_live_cliente_id(self, text):
        text = text.strip()
        if not text:
            self.view.txt_cliente_id.setStyleSheet("")
            return True
        if re.match(r"^\d{8}$", text):
            self.view.txt_cliente_id.setStyleSheet("")
            return True
        else:
            self.view.txt_cliente_id.setStyleSheet("border: 1px solid #c62828; background-color: #2d2d2d; color: #ffffff;")
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

    def validar_live_proveedor_id(self, text):
        text = text.strip()
        if not text:
            self.view.txt_proveedor_id.setStyleSheet("")
            return True
        if re.match(r"^\d{11}$", text):
            self.view.txt_proveedor_id.setStyleSheet("")
            return True
        else:
            self.view.txt_proveedor_id.setStyleSheet("border: 1px solid #c62828; background-color: #2d2d2d; color: #ffffff;")
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

    # --- DETECCION ASISTIDA DE ID EXISTENTE ---
    
    def detectar_cliente_existente(self):
        # No actuar si ya estamos editando o si la longitud no es válida para DNI (8 dígitos)
        if self.editando_cliente_id is not None:
            return
        
        id_text = self.view.txt_cliente_id.text().strip()
        if not id_text or len(id_text) < 8:
            return
            
        try:
            cliente_id = int(id_text)
        except ValueError:
            return
            
        db = SessionLocal()
        try:
            cli = db.query(Cliente).filter(Cliente.idCliente == cliente_id).first()
            if cli:
                reply = QMessageBox.question(
                    self.view,
                    "Cliente registrado",
                    f"El cliente con DNI/Código '{cliente_id}' ya se encuentra registrado.\n¿Desea cargar sus datos para editarlos?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.set_form_state_cliente("EDIT", cli)
        except Exception as e:
            print(f"Error al verificar cliente existente: {e}")
        finally:
            db.close()

    def detectar_proveedor_existente(self):
        # No actuar si ya estamos editando o si la longitud no es válida para RUC (11 dígitos)
        if self.editando_proveedor_id is not None:
            return
            
        id_text = self.view.txt_proveedor_id.text().strip()
        if not id_text or len(id_text) < 11:
            return
            
        try:
            proveedor_id = int(id_text)
        except ValueError:
            return
            
        db = SessionLocal()
        try:
            prov = db.query(Proveedor).filter(Proveedor.idProveedor == proveedor_id).first()
            if prov:
                reply = QMessageBox.question(
                    self.view,
                    "Proveedor registrado",
                    f"El proveedor con RUC/Código '{proveedor_id}' ya se encuentra registrado.\n¿Desea cargar sus datos para editarlos?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.set_form_state_proveedor("EDIT", prov)
        except Exception as e:
            print(f"Error al verificar proveedor existente: {e}")
        finally:
            db.close()

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
        id_text = self.view.txt_cliente_id.text().strip()
        nombre = self.view.txt_cliente_nombre.text().strip()
        telefono = self.view.txt_cliente_telefono.text().strip() or None
        correo = self.view.txt_cliente_correo.text().strip() or None
        
        if not id_text:
            QMessageBox.warning(self.view, "Campo requerido", "El campo DNI/Código es obligatorio.")
            return
        if not nombre:
            QMessageBox.warning(self.view, "Campo requerido", "El campo Nombres Completos es obligatorio.")
            return
            
        try:
            cliente_id = int(id_text)
        except ValueError:
            QMessageBox.warning(self.view, "Código inválido", "El Código/DNI debe ser un número entero válido.")
            return
            
        # Validación de formato de campos
        if not self.validar_live_cliente_id(id_text) and self.editando_cliente_id is None:
            QMessageBox.warning(self.view, "Código inválido", "El Código/DNI debe tener exactamente 8 dígitos.")
            return
        if correo and not self.validar_live_cliente_correo(correo):
            QMessageBox.warning(self.view, "Correo inválido", "El formato del correo electrónico es incorrecto.")
            return
            
        db = SessionLocal()
        try:
            if self.editando_cliente_id is None:
                # MODO CREACIÓN
                # Validación preventiva de duplicados
                existente = db.query(Cliente).filter(Cliente.idCliente == cliente_id).first()
                if existente:
                    QMessageBox.warning(self.view, "Código Duplicado", f"El cliente con DNI/Código '{cliente_id}' ya está registrado.")
                    return
                    
                nuevo_cliente = Cliente(
                    idCliente=cliente_id,
                    nombresCompletos=nombre,
                    telefono=telefono,
                    correoElectronico=correo
                )
                db.add(nuevo_cliente)
                db.commit()
                NotificationToast(self.view.window(), "✓ Cliente guardado exitosamente.")
            else:
                # MODO EDICIÓN
                cli = db.query(Cliente).filter(Cliente.idCliente == self.editando_cliente_id).first()
                if cli:
                    cli.nombresCompletos = nombre
                    cli.telefono = telefono
                    cli.correoElectronico = correo
                    db.commit()
                    NotificationToast(self.view.window(), "✓ Cliente actualizado exitosamente.")
                else:
                    QMessageBox.warning(self.view, "Error", "El cliente a editar ya no existe en la base de datos.")
                    
            self.limpiar_formulario_cliente()
            self.cargar_clientes()
        except IntegrityError as ie:
            db.rollback()
            QMessageBox.critical(self.view, "Error de Integridad", f"Fallo de integridad en base de datos. Posible código duplicado:\n{ie}")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self.view, "Error", f"Ocurrió un error inesperado al guardar:\n{e}")
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
        id_text = self.view.txt_proveedor_id.text().strip()
        nombre = self.view.txt_proveedor_nombre.text().strip()
        telefono = self.view.txt_proveedor_telefono.text().strip() or None
        direccion = self.view.txt_proveedor_direccion.text().strip() or None
        correo = self.view.txt_proveedor_correo.text().strip() or None
        
        if not id_text:
            QMessageBox.warning(self.view, "Campo requerido", "El campo RUC/Código es obligatorio.")
            return
        if not nombre:
            QMessageBox.warning(self.view, "Campo requerido", "El campo Razón Social es obligatorio.")
            return
            
        try:
            proveedor_id = int(id_text)
        except ValueError:
            QMessageBox.warning(self.view, "Código inválido", "El Código/RUC debe ser un número entero válido.")
            return
            
        # Validar formatos
        if not self.validar_live_proveedor_id(id_text) and self.editando_proveedor_id is None:
            QMessageBox.warning(self.view, "Código inválido", "El Código/RUC debe tener exactamente 11 dígitos.")
            return
        if correo and not self.validar_live_proveedor_correo(correo):
            QMessageBox.warning(self.view, "Correo inválido", "El formato del correo electrónico es incorrecto.")
            return
            
        db = SessionLocal()
        try:
            if self.editando_proveedor_id is None:
                # MODO CREACIÓN
                # Validación preventiva de duplicados
                existente = db.query(Proveedor).filter(Proveedor.idProveedor == proveedor_id).first()
                if existente:
                    QMessageBox.warning(self.view, "Código Duplicado", f"El proveedor con RUC/Código '{proveedor_id}' ya está registrado.")
                    return
                    
                nuevo_prov = Proveedor(
                    idProveedor=proveedor_id,
                    nombreRazonSocial=nombre,
                    telefono=telefono,
                    direccion=direccion,
                    correoElectronico=correo
                )
                db.add(nuevo_prov)
                db.commit()
                NotificationToast(self.view.window(), "✓ Proveedor guardado exitosamente.")
            else:
                # MODO EDICIÓN
                prov = db.query(Proveedor).filter(Proveedor.idProveedor == self.editando_proveedor_id).first()
                if prov:
                    prov.nombreRazonSocial = nombre
                    prov.telefono = telefono
                    prov.direccion = direccion
                    prov.correoElectronico = correo
                    db.commit()
                    NotificationToast(self.view.window(), "✓ Proveedor actualizado exitosamente.")
                else:
                    QMessageBox.warning(self.view, "Error", "El proveedor a editar ya no existe en la base de datos.")
                    
            self.limpiar_formulario_proveedor()
            self.cargar_proveedores()
        except IntegrityError as ie:
            db.rollback()
            QMessageBox.critical(self.view, "Error de Integridad", f"Fallo de integridad en base de datos. Posible código duplicado:\n{ie}")
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self.view, "Error", f"Ocurrió un error inesperado al guardar:\n{e}")
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
