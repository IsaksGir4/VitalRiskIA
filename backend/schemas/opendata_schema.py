from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class IPTRecord(BaseModel):
    codigo_dane: str
    nombre: str
    subregion: Optional[str]
    anio: int
    semana_epi: int
    fecha_semana: Optional[date]
    ipt_score: Optional[float]
    nivel_riesgo: Optional[str]
    casos_ira_total: Optional[int]
    tasa_ira_100k: Optional[float]
    pm25_avg: Optional[float]
    humedad_avg: Optional[float]
    temperatura_avg: Optional[float]
    periodo_pandemia: Optional[bool]

class AlertaRecord(BaseModel):
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
    fecha_generacion: Optional[datetime]