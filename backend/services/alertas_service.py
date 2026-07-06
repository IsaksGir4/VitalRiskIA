from sqlalchemy.orm import Session
from db.queries import get_media_historica_semana, get_media_historica_municipio

UMBRAL_NARANJA = 30.0
UMBRAL_ROJA    = 60.0

class AlertasService:

    @staticmethod
    def get_media_historica(
            db: Session, codigo_dane: str, semana_epi: int) -> float:
        media = get_media_historica_semana(db, codigo_dane, semana_epi)
        if media is None:
            media = get_media_historica_municipio(db, codigo_dane)
        return media

    @staticmethod
    def calcular_nivel_alerta(
            prediccion: float, media_historica: float) -> tuple[str, float]:
        if media_historica > 0:
            desviacion = (prediccion - media_historica) / media_historica * 100
        else:
            desviacion = 0.0

        if desviacion >= UMBRAL_ROJA:
            nivel = "ALERTA_ROJA"
        elif desviacion >= UMBRAL_NARANJA:
            nivel = "ALERTA_NARANJA"
        else:
            nivel = "ALERTA_VERDE"

        return nivel, round(desviacion, 2)