from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from api.routers import dashboard, inventario, pos, actores, compras
import os
from contextlib import asynccontextmanager
from config.db import SessionLocal, engine
from config.settings import CORS_ORIGINS
from models.base import Base
from models.catalogo import Producto
import models  # Asegura el registro central de todos los modelos SQLAlchemy
from services.mineria import MineriaService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inicializar conexión & 2. Crear tablas si no existen
    print("Verificando estructura de base de datos...")
    Base.metadata.create_all(bind=engine)

    # 3. Cargar datos iniciales si la base de datos está vacía
    db = SessionLocal()
    try:
        if db.query(Producto).first() is None:
            print("Base de datos vacía detectada. Iniciando carga inicial de datos...")
            try:
                from scripts.cargar_datos import cargar_datos
                cargar_datos()
                print("Carga inicial de datos completada exitosamente.")
            except Exception as e:
                print(f"Advertencia: Ocurrió un error en la carga inicial de datos: {e}")
        else:
            print("Base de datos existente con registros.")

        # Asegurar existencia de usuario por defecto para transacciones POS y Compras
        from api.dependencies import obtener_id_usuario_defecto
        obtener_id_usuario_defecto(db)

        # 4. Entrenar el modelo de minería Apriori
        print("Iniciando entrenamiento del motor de Minería Apriori...")
        MineriaService.entrenar_modelo(db)
        print(f"Modelo Apriori entrenado. {len(MineriaService._reglas)} antecedentes en base de conocimiento.")
    finally:
        db.close()

    yield
    # Shutdown logic
    print("Apagando el sistema...")

app = FastAPI(
    title="Smart Boutique POS - API",
    description="API RESTful para el sistema de ventas e inventario inteligente",
    version="1.0.0",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

import time
STATIC_VERSION = str(int(time.time()))

# Configurar motor de plantillas Jinja2
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")
templates.env.globals["STATIC_VERSION"] = STATIC_VERSION
templates.env.cache = None

# Incluir routers
app.include_router(dashboard.router)
app.include_router(inventario.router)
app.include_router(pos.router)
app.include_router(actores.router)
app.include_router(compras.router)

# Rutas para servir vistas HTML
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/dashboard")
def view_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/inventario")
def view_inventario(request: Request):
    return templates.TemplateResponse(request=request, name="inventario.html")

@app.get("/pos")
def view_pos(request: Request):
    return templates.TemplateResponse(request=request, name="pos.html")

@app.get("/actores")
def view_actores(request: Request):
    return templates.TemplateResponse(request=request, name="actores.html")

@app.get("/compras")
def view_compras(request: Request):
    return templates.TemplateResponse(request=request, name="compras.html")
