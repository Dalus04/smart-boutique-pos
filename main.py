import sys
import uvicorn

def main():
    print("Iniciando Smart Boutique POS - Web API (FastAPI)...")
    try:
        uvicorn.run("api.main_api:app", host="0.0.0.0", port=8000, reload=False)
    except KeyboardInterrupt:
        print("Servidor detenido manualmente.")
    except Exception as e:
        print(f"Error fatal iniciando el servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
