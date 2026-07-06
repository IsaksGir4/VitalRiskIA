from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from settings.dependencies import get_db
from db.queries import get_alertas_activas, get_alertas_municipio, get_municipio
from utils import safe_float

router = APIRouter()

@router.get("/activas", tags=["HU17 — Alertas"],
            summary="Alertas ROJA y NARANJA más recientes")
def alertas_activas(
    nivel: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if nivel and nivel not in (
            "ALERTA_ROJA", "ALERTA_NARANJA", "ALERTA_VERDE"):
        raise HTTPException(status_code=400,
            detail="nivel debe ser ALERTA_ROJA, ALERTA_NARANJA o ALERTA_VERDE")

    rows = get_alertas_activas(db, nivel)
    return {
        "alertas": [{
            "codigo_dane":      r.codigo_dane,
            "nombre":           r.nombre,
            "subregion":        r.subregion,
            "anio":             r.anio,
            "semana_epi":       r.semana_epi,
            "nivel_alerta":     r.nivel_alerta,
            "prediccion_casos": safe_float(r.prediccion_casos),
            "desviacion_pct":   safe_float(r.desviacion_pct),
            "variable_causal":  r.variable_causal,
            "media_historica":  safe_float(r.media_historica),
        } for r in rows],
        "total": len(rows),
        "metadata": {
            "ROJA":    "> 60% sobre media histórica",
            "NARANJA": "30-60% sobre media histórica"
        }
    }

@router.get("/{codigo_dane}", tags=["HU17 — Alertas"],
            summary="Historial de alertas de un municipio")
def alertas_municipio(
    codigo_dane: str,
    anio: Optional[int] = None,
    db: Session = Depends(get_db)
):
    codigo_dane = codigo_dane.zfill(5)
    mun = get_municipio(db, codigo_dane)
    if not mun:
        raise HTTPException(status_code=404,
            detail=f"Municipio {codigo_dane} no encontrado")

    rows = get_alertas_municipio(db, codigo_dane, anio)
    resumen = {"ALERTA_ROJA": 0, "ALERTA_NARANJA": 0, "ALERTA_VERDE": 0}
    alertas = []
    for r in rows:
        if r.nivel_alerta in resumen:
            resumen[r.nivel_alerta] += 1
        alertas.append({
            "anio":             r.anio,
            "semana_epi":       r.semana_epi,
            "nivel_alerta":     r.nivel_alerta,
            "prediccion_casos": safe_float(r.prediccion_casos),
            "desviacion_pct":   safe_float(r.desviacion_pct),
            "variable_causal":  r.variable_causal,
            "media_historica":  safe_float(r.media_historica),
        })

    return {
        "codigo_dane":     codigo_dane,
        "nombre":          mun.nombre,
        "total_semanas":   len(alertas),
        "resumen_alertas": resumen,
        "alertas":         alertas
    }