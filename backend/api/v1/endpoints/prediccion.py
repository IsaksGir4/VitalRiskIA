import math
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas.prediccion_schema import PrediccionRequest, PrediccionResponse
from services.ml_service import MLService
from services.alertas_service import AlertasService
from settings.dependencies import get_db
from utils import safe_float

router = APIRouter()

@router.post("/", response_model=PrediccionResponse,
             tags=["HU18 — Predicción"],
             summary="Predice casos IRA semana t+1")
def predecir(
    request: PrediccionRequest,
    db: Session = Depends(get_db)
):
    ml = MLService.get_instance()
    if ml.modelo is None:
        raise HTTPException(status_code=503,
            detail="Modelo XGBoost no disponible")

    media = AlertasService.get_media_historica(
        db, request.codigo_dane, request.semana_epi)

    semana_sin = float(np.sin(2 * np.pi * request.semana_epi / 52))
    semana_cos = float(np.cos(2 * np.pi * request.semana_epi / 52))
    casos_actual = request.casos_ira_total or media
    desv_hist = ((casos_actual - media) / media * 100
                 if media > 0 else 0.0)

    feature_values = {
        **request.model_dump(),
        "media_hist_mun_sem":      media,
        "desviacion_vs_historico": desv_hist,
        "semana_sin":              semana_sin,
        "semana_cos":              semana_cos,
    }

    pred, variable_causal = ml.predict(feature_values)

    # Verificar que la predicción es un número válido
    if math.isnan(pred) or math.isinf(pred):
        pred = 0.0

    nivel, desviacion = AlertasService.calcular_nivel_alerta(pred, media)

    return PrediccionResponse(
        codigo_dane=         request.codigo_dane,
        semana_epi=          request.semana_epi,
        anio=                request.anio,
        prediccion_casos_t1= round(pred, 2),
        nivel_alerta=        nivel,
        variable_causal=     variable_causal,
        desviacion_pct=      safe_float(desviacion),
        mensaje=(f"Predicción semana {request.semana_epi + 1} de {request.anio}. "
                 f"Desviación {desviacion:+.1f}% sobre media histórica.")
    )