import customtkinter

class MainWindow(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # Configurar ventana principal
        self.title("BoutiqueIQ - POS")
        self.geometry("1024x768")
        self.minsize(800, 600)

        # Configurar layout de grilla (1 fila, 2 columnas)
        # Columna 0: Barra lateral (ancho fijo, no se estira)
        # Columna 1: Panel de contenido (ocupa el espacio restante)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ------------------ BARRA LATERAL (SIDEBAR) ------------------
        self.sidebar_frame = customtkinter.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # Reservar filas para botones y empujar el selector de apariencia abajo
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        # Título / Logo de la Aplicación
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame, 
            text="BoutiqueIQ", 
            font=customtkinter.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Botones de Navegación (con estilos uniformes y anchors)
        self.btn_dashboard = customtkinter.CTkButton(
            self.sidebar_frame, 
            text="Dashboard", 
            anchor="w",
            command=self.nav_dashboard
        )
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_nueva_venta = customtkinter.CTkButton(
            self.sidebar_frame, 
            text="Nueva Venta", 
            anchor="w",
            command=self.nav_nueva_venta
        )
        self.btn_nueva_venta.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.btn_catalogo = customtkinter.CTkButton(
            self.sidebar_frame, 
            text="Catálogo", 
            anchor="w",
            command=self.nav_catalogo
        )
        self.btn_catalogo.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.btn_inventario = customtkinter.CTkButton(
            self.sidebar_frame, 
            text="Inventario", 
            anchor="w",
            command=self.nav_inventario
        )
        self.btn_inventario.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        self.btn_clientes = customtkinter.CTkButton(
            self.sidebar_frame, 
            text="Clientes", 
            anchor="w",
            command=self.nav_clientes
        )
        self.btn_clientes.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        # Selector de Apariencia (Modo Claro/Oscuro) en la parte inferior
        self.appearance_mode_label = customtkinter.CTkLabel(
            self.sidebar_frame, 
            text="Modo de Color:", 
            anchor="w"
        )
        self.appearance_mode_label.grid(row=7, column=0, padx=20, pady=(10, 0), sticky="ew")
        
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame, 
            values=["Dark", "Light", "System"],
            command=self.change_appearance_mode_event
        )
        self.appearance_mode_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.appearance_mode_optionemenu.set("Dark")

        # ------------------ PANEL DE CONTENIDO (CONTENT FRAME) ------------------
        self.content_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Label de bienvenida provisional
        self.welcome_label = customtkinter.CTkLabel(
            self.content_frame, 
            text="Bienvenido a BoutiqueIQ POS\n\nSeleccione una opción en el menú lateral para comenzar.", 
            font=customtkinter.CTkFont(size=16)
        )
        self.welcome_label.grid(row=0, column=0, padx=20, pady=20)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def clear_content_frame(self):
        """
        Elimina todos los widgets dentro de content_frame para evitar fugas de memoria.
        """
        for child in self.content_frame.winfo_children():
            child.destroy()

    # Funciones de navegación para las diferentes vistas
    def nav_dashboard(self):
        print("Navegando a Dashboard")
        self.clear_content_frame()
        lbl = customtkinter.CTkLabel(self.content_frame, text="Vista Dashboard (En desarrollo)", font=customtkinter.CTkFont(size=16))
        lbl.grid(row=0, column=0, padx=20, pady=20)

    def nav_nueva_venta(self):
        print("Navegando a Nueva Venta")
        self.clear_content_frame()
        from ui.views.pos_view import POSView
        self.pos_view = POSView(self.content_frame)
        self.pos_view.grid(row=0, column=0, sticky="nsew")

    def nav_catalogo(self):
        print("Navegando a Catálogo")
        self.clear_content_frame()
        lbl = customtkinter.CTkLabel(self.content_frame, text="Vista Catálogo (En desarrollo)", font=customtkinter.CTkFont(size=16))
        lbl.grid(row=0, column=0, padx=20, pady=20)

    def nav_inventario(self):
        print("Navegando a Inventario")
        self.clear_content_frame()
        lbl = customtkinter.CTkLabel(self.content_frame, text="Vista Inventario (En desarrollo)", font=customtkinter.CTkFont(size=16))
        lbl.grid(row=0, column=0, padx=20, pady=20)

    def nav_clientes(self):
        print("Navegando a Clientes")
        self.clear_content_frame()
        lbl = customtkinter.CTkLabel(self.content_frame, text="Vista Clientes (En desarrollo)", font=customtkinter.CTkFont(size=16))
        lbl.grid(row=0, column=0, padx=20, pady=20)
