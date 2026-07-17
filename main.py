import sys
import tkinter.messagebox as messagebox
from config.db import engine

# Importar customtkinter y configurar comportamiento inicial
import customtkinter
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")

def main():
    print("Iniciando BoutiqueIQ...")
    print("Verificando conexión con la base de datos...")
    
    try:
        # Intentar conectar con la base de datos para validar credenciales y estado del servidor
        with engine.connect() as connection:
            print("Conexión exitosa a la base de datos.")
    except Exception as e:
        print(f"Error crítico de conexión: {e}")
        # Mostrar diálogo de error utilizando tkinter sin levantar la ventana principal de tkinter
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Ocultar la ventana raíz vacía de tkinter
        messagebox.showerror(
            "Error de Conexión",
            f"No se pudo conectar a la base de datos MySQL.\n\nDetalle: {str(e)}\n\n"
            f"Por favor, verifique que el servicio de MySQL esté corriendo y que "
            f"las credenciales en el archivo .env sean correctas."
        )
        root.destroy()
        sys.exit(1)

    # Si la conexión es exitosa, instanciar la ventana principal y arrancar la UI
    from ui.main_window import MainWindow
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
