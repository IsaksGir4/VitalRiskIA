from pydantic import BaseModel
from typing import Optional

class AlertaItem(BaseModel):
    codigo_dane: str
    nombre: str
    subregion: Optional[str]
    anio: int
    semana_epi: int
    nivel_alerta: str
    prediccion_casos: Optional[float]
    desviacion_pct: Optional[float]
    variable_causal: Optional[str]
    media_historica: Optional[float]

class AlertasActivasResponse(BaseModel):
    alertas: list[AlertaItem]
    total: int
    metadata: dict

class AlertaHistorialItem(BaseModel):
    anio: int
    semana_epi: int
    nivel_alerta: str
    prediccion_casos: Optional[float]
    desviacion_pct: Optional[float]
    variable_causal: Optional[str]
    media_historica: Optional[float]

class AlertasMunicipioResponse(BaseModel):
    codigo_dane: str
    nombre: str
    total_semanas: int
    resumen_alertas: dict
    alertas: list[AlertaHistorialItem]