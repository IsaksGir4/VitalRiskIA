from fastapi import APIRouter
from api.v1.endpoints import health, mapa, alertas, prediccion, opendata, modelo, etl

api_router = APIRouter()

api_router.include_router(health.router,     prefix="/health")
api_router.include_router(mapa.router,       prefix="/mapa")
api_router.include_router(alertas.router,    prefix="/alertas")
api_router.include_router(prediccion.router, prefix="/prediccion")
api_router.include_router(opendata.router,   prefix="/opendata")
api_router.include_router(modelo.router,     prefix="/modelo")
api_router.include_router(etl.router,        prefix="/etl")