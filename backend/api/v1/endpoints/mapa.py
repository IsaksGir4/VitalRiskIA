from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from settings.dependencies import get_db
from services.geo_service import GeoService
from db.queries import get_mapa_riesgo_anual, get_mapa_riesgo_semana, get_ultima_semana_disponible
router = APIRouter()

@router.get("/riesgo", tags=["HU16 — Mapa Geoespacial"],
            summary="GeoJSON con IPT y nivel de riesgo por municipio")
def mapa_riesgo(
    anio: int = 2023,
    semana_epi: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if semana_epi:
        rows = get_mapa_riesgo_semana(db, anio, semana_epi)
    else:
        rows = get_mapa_riesgo_anual(db, anio)

    if not rows:
        raise HTTPException(status_code=404,
            detail=f"Sin datos para anio={anio}"
                   + (f" semana={semana_epi}" if semana_epi else ""))

    return GeoService.build_geojson(rows, anio, semana_epi)
@router.get("/ultima_fecha", tags=["HU18 — Filtros Dinámicos"], summary="Obtiene la fecha más reciente con datos")
def ultima_fecha(db: Session = Depends(get_db)):
    data = get_ultima_semana_disponible(db)
    if not data:
        raise HTTPException(status_code=404, detail="No hay datos en el sistema")
    return data