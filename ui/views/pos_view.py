import customtkinter

class POSView(customtkinter.CTkFrame):
    # Definición de Constantes Tipográficas para asegurar legibilidad y consistencia
    FONT_HEADER = ("Segoe UI", 18, "bold")
    FONT_SUBHEADER = ("Segoe UI", 14, "bold")
    FONT_BODY = ("Segoe UI", 12, "normal")
    FONT_BODY_BOLD = ("Segoe UI", 12, "bold")
    FONT_TOTAL = ("Segoe UI", 22, "bold")

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        
        # Configurar grilla del contenedor principal (1 fila, 2 columnas)
        # Columna 0: Panel de Trabajo (Búsqueda + Carrito) - Se expande
        # Columna 1: Panel de Control (Cobro + Venta Cruzada) - Ancho fijo mínimo
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=350)
        self.grid_rowconfigure(0, weight=1)

        # ------------------ COLUMNA IZQUIERDA: TRABAJO ------------------
        # Descompresión visual mediante margen externo adecuado
        self.left_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.left_container.grid(row=0, column=0, padx=(15, 8), pady=12, sticky="nsew")
        self.left_container.grid_columnconfigure(0, weight=1)
        self.left_container.grid_rowconfigure(0, weight=0)  # Panel Búsqueda
        self.left_container.grid_rowconfigure(1, weight=1)  # Panel Carrito

        # 1. Panel de Búsqueda (Con fondo contrastado oscuro)
        self.search_frame = customtkinter.CTkFrame(self.left_container, fg_color="#212121")
        self.search_frame.grid(row=0, column=0, padx=5, pady=(0, 12), sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)
        self.search_frame.grid_columnconfigure(1, weight=0)

        self.search_entry = customtkinter.CTkEntry(
            self.search_frame, 
            placeholder_text="Buscar producto por código de barras o nombre...",
            font=self.FONT_BODY
        )
        self.search_entry.grid(row=0, column=0, padx=(15, 12), pady=15, sticky="ew")

        self.search_button = customtkinter.CTkButton(
            self.search_frame, 
            text="Buscar / Agregar", 
            width=130,
            font=self.FONT_BODY_BOLD,
            command=self.search_product_event
        )
        self.search_button.grid(row=0, column=1, padx=(0, 15), pady=15)

        # 2. Panel del Carrito (Fondo gris oscuro diferenciado)
        self.cart_frame = customtkinter.CTkFrame(self.left_container, fg_color="#212121")
        self.cart_frame.grid(row=1, column=0, padx=5, pady=0, sticky="nsew")
        self.cart_frame.grid_columnconfigure(0, weight=1)
        self.cart_frame.grid_rowconfigure(0, weight=0)  # Cabecera
        self.cart_frame.grid_rowconfigure(1, weight=1)  # Items scrollables

        # Cabecera de la tabla
        self.header_frame = customtkinter.CTkFrame(self.cart_frame, fg_color="transparent", height=35)
        self.header_frame.grid(row=0, column=0, padx=15, pady=(12, 6), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=5)  # Producto
        self.header_frame.grid_columnconfigure(1, weight=2)  # Precio Unit.
        self.header_frame.grid_columnconfigure(2, weight=2)  # Cantidad
        self.header_frame.grid_columnconfigure(3, weight=2)  # Subtotal
        self.header_frame.grid_columnconfigure(4, weight=1)  # Acción

        headers = ["Producto", "Precio Unit.", "Cantidad", "Subtotal", "Acción"]
        for col_idx, text in enumerate(headers):
            anchor_dir = "w" if col_idx == 0 else "center"
            lbl = customtkinter.CTkLabel(
                self.header_frame, 
                text=text, 
                font=self.FONT_BODY_BOLD,
                anchor=anchor_dir
            )
            lbl.grid(row=0, column=col_idx, sticky="ew")

        # Scrollable frame para los items
        self.items_scroll_frame = customtkinter.CTkScrollableFrame(self.cart_frame, fg_color="transparent")
        self.items_scroll_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.items_scroll_frame.grid_columnconfigure(0, weight=1)

        # Datos dummy iniciales para el carrito
        self.dummy_cart_items = [
            {"id": 1, "nombre": "Casaca de Cuero Premium - Negra (M)", "precio": 120.00, "cantidad": 1},
            {"id": 2, "nombre": "Zapatillas Deportivas Running RunFast (42)", "precio": 85.50, "cantidad": 2},
        ]
        
        # ------------------ COLUMNA DERECHA: CONTROL ------------------
        # Espaciado y ordenación visual clara
        self.right_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.right_container.grid(row=0, column=1, padx=(8, 15), pady=12, sticky="nsew")
        self.right_container.grid_columnconfigure(0, weight=1)
        self.right_container.grid_rowconfigure(0, weight=0)  # Cobro
        self.right_container.grid_rowconfigure(1, weight=1)  # Venta Cruzada

        # 1. Panel de Cobro (Cálculos + Acción, fondo gris oscuro plano)
        self.checkout_frame = customtkinter.CTkFrame(self.right_container, fg_color="#1e1e1e")
        self.checkout_frame.grid(row=0, column=0, padx=5, pady=(0, 12), sticky="ew")
        self.checkout_frame.grid_columnconfigure(0, weight=1)
        self.checkout_frame.grid_columnconfigure(1, weight=1)

        # Subtotal
        self.lbl_subtotal_title = customtkinter.CTkLabel(self.checkout_frame, text="Subtotal:", font=self.FONT_BODY, anchor="w")
        self.lbl_subtotal_title.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.lbl_subtotal_val = customtkinter.CTkLabel(self.checkout_frame, text="S/ 0.00", font=self.FONT_BODY_BOLD)
        self.lbl_subtotal_val.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="e")

        # IGV
        self.lbl_igv_title = customtkinter.CTkLabel(self.checkout_frame, text="IGV (18%):", font=self.FONT_BODY, anchor="w")
        self.lbl_igv_title.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.lbl_igv_val = customtkinter.CTkLabel(self.checkout_frame, text="S/ 0.00", font=self.FONT_BODY_BOLD)
        self.lbl_igv_val.grid(row=1, column=1, padx=20, pady=5, sticky="e")

        # Total (Tipografía ampliada y color verde destacado)
        self.lbl_total_title = customtkinter.CTkLabel(
            self.checkout_frame, 
            text="Total:", 
            font=self.FONT_SUBHEADER, 
            anchor="w"
        )
        self.lbl_total_title.grid(row=2, column=0, padx=20, pady=(8, 20), sticky="w")
        
        self.lbl_total_val = customtkinter.CTkLabel(
            self.checkout_frame, 
            text="S/ 0.00", 
            font=self.FONT_TOTAL,
            text_color="#2ecc71"
        )
        self.lbl_total_val.grid(row=2, column=1, padx=20, pady=(8, 20), sticky="e")

        # Botón Cobrar (Tamaño generoso y espaciado claro)
        self.btn_cobrar = customtkinter.CTkButton(
            self.checkout_frame, 
            text="COBRAR", 
            fg_color="#2ecc71", 
            hover_color="#27ae60",
            font=self.FONT_HEADER,
            height=50,
            command=self.cobrar_event
        )
        self.btn_cobrar.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")

        # 2. Panel de Venta Cruzada (Sugerencias, con fondo gris oscuro plano)
        self.suggestions_frame = customtkinter.CTkFrame(self.right_container, fg_color="#1e1e1e")
        self.suggestions_frame.grid(row=1, column=0, padx=5, pady=0, sticky="nsew")
        self.suggestions_frame.grid_columnconfigure(0, weight=1)
        self.suggestions_frame.grid_rowconfigure(0, weight=0)  # Título
        self.suggestions_frame.grid_rowconfigure(1, weight=1)  # Lista Sugerencias

        self.lbl_sug_title = customtkinter.CTkLabel(
            self.suggestions_frame, 
            text="Recomendaciones Inteligentes", 
            font=self.FONT_SUBHEADER
        )
        self.lbl_sug_title.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        self.sug_content_frame = customtkinter.CTkScrollableFrame(self.suggestions_frame, fg_color="transparent")
        self.sug_content_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.sug_content_frame.grid_columnconfigure(0, weight=1)

        # Datos dummy de sugerencia
        self.dummy_suggestions = [
            {"id": 3, "nombre": "Medias Deportivas Comfort (Pack x3)", "precio": 15.00, "confianza": "95%"},
            {"id": 4, "nombre": "Correa de Cuero Formal - Marrón", "precio": 35.00, "confianza": "80%"}
        ]

        # Renderizar la interfaz inicial
        self.recalculate_totals()
        self.render_cart()
        self.render_suggestions()

    def render_cart(self):
        # Limpiar elementos del scroll del carrito
        for child in self.items_scroll_frame.winfo_children():
            child.destroy()
            
        for idx, item in enumerate(self.dummy_cart_items):
            # Filas con fondo "#2B2B2B" para contrastar con el fondo "#212121" del contenedor principal
            row_frame = customtkinter.CTkFrame(self.items_scroll_frame, fg_color="#2b2b2b")
            row_frame.grid(row=idx, column=0, pady=6, padx=2, sticky="ew")
            row_frame.grid_columnconfigure(0, weight=5)  # Nombre
            row_frame.grid_columnconfigure(1, weight=2)  # Precio Unit.
            row_frame.grid_columnconfigure(2, weight=2)  # Cantidad
            row_frame.grid_columnconfigure(3, weight=2)  # Subtotal
            row_frame.grid_columnconfigure(4, weight=1)  # Acción (X)

            # Nombre
            lbl_nombre = customtkinter.CTkLabel(
                row_frame, 
                text=item["nombre"], 
                anchor="w", 
                font=self.FONT_BODY_BOLD
            )
            lbl_nombre.grid(row=0, column=0, sticky="w", padx=12, pady=10)

            # Precio
            lbl_precio = customtkinter.CTkLabel(row_frame, text=f"S/ {item['precio']:.2f}", font=self.FONT_BODY)
            lbl_precio.grid(row=0, column=1, padx=8, pady=10)

            # Cantidad (Controles - y + de buen tamaño)
            qty_frame = customtkinter.CTkFrame(row_frame, fg_color="transparent")
            qty_frame.grid(row=0, column=2, padx=8, pady=10)
            
            btn_minus = customtkinter.CTkButton(
                qty_frame, text="-", width=30, height=30,
                font=self.FONT_BODY_BOLD,
                command=lambda i=item: self.update_qty(i, -1)
            )
            btn_minus.grid(row=0, column=0, padx=2)
            
            lbl_qty = customtkinter.CTkLabel(qty_frame, text=str(item["cantidad"]), width=35, font=self.FONT_BODY_BOLD)
            lbl_qty.grid(row=0, column=1, padx=2)
            
            btn_plus = customtkinter.CTkButton(
                qty_frame, text="+", width=30, height=30,
                font=self.FONT_BODY_BOLD,
                command=lambda i=item: self.update_qty(i, 1)
            )
            btn_plus.grid(row=0, column=2, padx=2)

            # Subtotal
            subtotal = item["precio"] * item["cantidad"]
            lbl_subtotal = customtkinter.CTkLabel(row_frame, text=f"S/ {subtotal:.2f}", font=self.FONT_BODY_BOLD, text_color="#2ecc71")
            lbl_subtotal.grid(row=0, column=3, padx=8, pady=10)

            # Eliminar
            btn_del = customtkinter.CTkButton(
                row_frame, 
                text="X", 
                width=30, 
                height=30, 
                fg_color="#e74c3c", 
                hover_color="#c0392b",
                font=("Segoe UI", 10, "normal"),
                command=lambda i=item: self.remove_item(i)
            )
            btn_del.grid(row=0, column=4, padx=12, pady=10)

    def render_suggestions(self):
        # Limpiar sugerencias previas
        for child in self.sug_content_frame.winfo_children():
            child.destroy()

        for idx, sug in enumerate(self.dummy_suggestions):
            # Tarjetas de sugerencias con fondo gris "#2D2D2D" para contrastar con el fondo "#1E1E1E"
            card = customtkinter.CTkFrame(self.sug_content_frame, fg_color="#2d2d2d", height=90)
            card.grid(row=idx, column=0, pady=6, padx=5, sticky="ew")
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)
            card.grid_rowconfigure(0, weight=1)

            # Información de la recomendación
            info_frame = customtkinter.CTkFrame(card, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=12, pady=8, sticky="nsew")
            info_frame.grid_columnconfigure(0, weight=1)
            info_frame.grid_rowconfigure(0, weight=1)
            info_frame.grid_rowconfigure(1, weight=1)
            
            lbl_sug_name = customtkinter.CTkLabel(
                info_frame, 
                text=sug["nombre"], 
                font=self.FONT_BODY_BOLD,
                anchor="w"
            )
            lbl_sug_name.grid(row=0, column=0, sticky="w")
            
            lbl_sug_details = customtkinter.CTkLabel(
                info_frame, 
                text=f"S/ {sug['precio']:.2f}  •  Confianza: {sug['confianza']}", 
                font=self.FONT_BODY, 
                text_color="#95a5a6",
                anchor="w"
            )
            lbl_sug_details.grid(row=1, column=0, sticky="w")

            # Botón rápido para agregar
            btn_add_sug = customtkinter.CTkButton(
                card, 
                text="+", 
                width=35, 
                height=35,
                font=self.FONT_SUBHEADER,
                command=lambda s=sug: self.add_suggestion_to_cart(s)
            )
            btn_add_sug.grid(row=0, column=1, padx=12, pady=10)

    def update_qty(self, item, change):
        new_qty = item["cantidad"] + change
        if new_qty > 0:
            item["cantidad"] = new_qty
            self.recalculate_totals()
            self.render_cart()

    def remove_item(self, item):
        self.dummy_cart_items = [i for i in self.dummy_cart_items if i["id"] != item["id"]]
        self.recalculate_totals()
        self.render_cart()

    def add_suggestion_to_cart(self, sug):
        # Si ya existe en el carrito, se incrementa la cantidad
        for item in self.dummy_cart_items:
            if item["id"] == sug["id"]:
                item["cantidad"] += 1
                self.recalculate_totals()
                self.render_cart()
                return
        
        # Si no existe, se añade una nueva fila
        self.dummy_cart_items.append({
            "id": sug["id"],
            "nombre": sug["nombre"],
            "precio": sug["precio"],
            "cantidad": 1
        })
        self.recalculate_totals()
        self.render_cart()

    def recalculate_totals(self):
        total = sum(item["precio"] * item["cantidad"] for item in self.dummy_cart_items)
        subtotal = total / 1.18
        igv = total - subtotal
        
        self.lbl_subtotal_val.configure(text=f"S/ {subtotal:.2f}")
        self.lbl_igv_val.configure(text=f"S/ {igv:.2f}")
        self.lbl_total_val.configure(text=f"S/ {total:.2f}")

    def search_product_event(self):
        search_query = self.search_entry.get().strip()
        if not search_query:
            return
        
        # Simular búsqueda y adición de un nuevo producto
        new_id = len(self.dummy_cart_items) + 100
        self.dummy_cart_items.append({
            "id": new_id,
            "nombre": f"Producto Encontrado: {search_query}",
            "precio": 45.00,
            "cantidad": 1
        })
        self.recalculate_totals()
        self.render_cart()
        self.search_entry.delete(0, 'end')

    def cobrar_event(self):
        print("Procesando cobro del carrito...")
