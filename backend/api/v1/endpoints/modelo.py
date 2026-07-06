from fastapi import APIRouter
from services.ml_service import MLService

router = APIRouter()

@router.get(
    "/metricas",
    tags=["Transparencia IA"],
    summary="Métricas de rendimiento y variables del modelo XGBoost"
)
def metricas_modelo():
    """
    Retorna las métricas de validación, feature importance y configuración
    del modelo XGBoost entrenado. Cumple el criterio de interpretabilidad
    de la rúbrica MinTIC (Nivel Intermedio).
    """
    return MLService.get_instance().get_model_metadata()