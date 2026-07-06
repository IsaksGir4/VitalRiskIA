from pydantic import BaseModel, field_validator
from typing import Optional

class PrediccionRequest(BaseModel):
    codigo_dane: str
    semana_epi: int
    anio: int
    casos_ira_total:  Optional[float] = None
    casos_ira_lag1:   Optional[float] = None
    pm25_avg:         Optional[float] = None
    pm25_lag1:        Optional[float] = None
    humedad_avg:      Optional[float] = None
    icv_seg_social:   Optional[float] = None
    icv_score:        Optional[float] = None
    ipm_pct:          Optional[float] = None

    @field_validator("codigo_dane")
    @classmethod
    def pad_codigo_dane(cls, v: str) -> str:
        return v.zfill(5)

    @field_validator("semana_epi")
    @classmethod
    def validar_semana(cls, v: int) -> int:
        if not 1 <= v <= 53:
            raise ValueError("semana_epi debe estar entre 1 y 53")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "codigo_dane": "05001",
                "semana_epi": 15,
                "anio": 2024,
                "casos_ira_total": 5,
                "casos_ira_lag1": 4,
                "pm25_avg": 18.5,
                "humedad_avg": 72.3,
                "icv_seg_social": 3.1
            }
        }
    }

class PrediccionResponse(BaseModel):
    codigo_dane: str
    semana_epi: int
    anio: int
    prediccion_casos_t1: float
    nivel_alerta: str
    variable_causal: str
    desviacion_pct: Optional[float] = None
    mensaje: str