from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.api import api_router
from settings.config import settings
from services.ml_service import MLService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: precarga el modelo una sola vez en memoria
    MLService.get_instance()
    yield
    # Shutdown: aquí irían cleanup tasks si las hubiera

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
Sistema Inteligente de Vigilancia Preventiva Territorial en Salud.

Predice brotes de IRA con una semana de anticipación para los 103 municipios
de Antioquia, integrando datos de calidad del aire (IDEAM), epidemiología
(SIVIGILA/INS) y variables socioeconómicas (DANE/ECV 2023).

**Equipo 326 | Datos al Ecosistema 2026 — IA para Colombia (MinTIC)**
    """,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")