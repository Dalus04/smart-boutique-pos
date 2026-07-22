from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from api.routers import dashboard, inventario, pos, actores, compras
import os
from contextlib import asynccontextmanager
from config.db import SessionLocal
from config.settings import CORS_ORIGINS
from services.mineria import MineriaService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Entrenar modelo Apriori de forma lazy cargándolo a memoria
    print("Iniciando entrenamiento del motor de Minería Apriori...")
    db = SessionLocal()
    try:
        MineriaService.entrenar_modelo(db)
        print(f"Modelo Apriori entrenado. {len(MineriaService._reglas)} antecedentes en base de conocimiento.")
    finally:
        db.close()
    yield
    # Shutdown logic if any
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

# Configurar motor de plantillas Jinja2
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")
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
