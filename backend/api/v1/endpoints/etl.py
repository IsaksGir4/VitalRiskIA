"""
Endpoint ETL — Dispara el pipeline de sincronización con datos.gov.co
=====================================================================
POST /api/v1/etl/sincronizar   → Pipeline completo (Extract + Transform + Load)
GET  /api/v1/etl/estado        → Último estado de sincronización
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from settings.dependencies import get_db
from services.etl_service import ETLService

router = APIRouter()

# Cache del último resultado (en memoria — simple para MVP)
_ultimo_resultado: dict = {}


@router.post(
    "/sincronizar",
    tags=["ETL — Datos en Tiempo Real"],
    summary="Ejecuta el pipeline ETL desde APIs Socrata (IDEAM)",
)
def sincronizar_clima(
    dias_atras: int = Query(14, ge=1, le=90, description="Días hacia atrás para extraer"),
    semana_epi: Optional[int] = Query(None, ge=1, le=53, description="Semana epidemiológica específica"),
    anio: Optional[int] = Query(None, ge=2024, le=2030, description="Año específico"),
    db: Session = Depends(get_db),
):
    """
    Ejecuta el pipeline ETL completo:

    1. **Extract**: Descarga datos climáticos recientes de las APIs Socrata
       de datos.gov.co (humedad, temperatura, precipitación, presión).
    2. **Transform**: Agrega por municipio × semana epidemiológica,
       calcula lags y features derivadas.
    3. **Load**: UPSERT en fact_riesgo_territorial, ejecuta XGBoost,
       genera alertas en alertas_territoriales.

    **Fuentes Socrata consultadas:**
    - Humedad del Aire (uext-mhny)
    - Temperatura Ambiente (sbwg-7ju4)
    - Precipitación (s54a-sgyg)
    - Presión Atmosférica (62tk-nxj5)

    **Uso recomendado:** Ejecutar semanalmente (domingo) o antes de
    una demostración para tener datos actualizados.
    """
    global _ultimo_resultado

    resultado = ETLService.ejecutar_pipeline(
        db=db,
        dias_atras=dias_atras,
        semana_override=semana_epi,
        anio_override=anio,
    )

    _ultimo_resultado = resultado
    return resultado


@router.get(
    "/estado",
    tags=["ETL — Datos en Tiempo Real"],
    summary="Estado de la última sincronización ETL",
)
def estado_etl():
    """Retorna el resultado de la última ejecución del pipeline ETL."""
    if not _ultimo_resultado:
        return {
            "status": "sin_ejecucion",
            "mensaje": "El pipeline ETL no ha sido ejecutado en esta sesión.",
            "instruccion": "POST /api/v1/etl/sincronizar para ejecutar.",
        }
    return _ultimo_resultado