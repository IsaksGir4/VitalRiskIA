from fastapi import APIRouter
from sqlalchemy import text
from db.database import engine
from services.ml_service import MLService

router = APIRouter()

@router.get("/", tags=["Sistema"],
            summary="Estado del sistema")
def health_check():
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    ml = MLService.get_instance()
    model_ok = ml.modelo is not None

    return {
        "status":   "OK" if (db_ok and model_ok) else "DEGRADADO",
        "version":  "1.0.0",
        "equipo":   "326",
        "concurso": "Datos al Ecosistema 2026",
        "dependencias": {
            "base_de_datos":   "OK" if db_ok    else "ERROR",
            "modelo_xgboost":  "OK" if model_ok else "ERROR",
            "features_modelo": len(ml.features)
        }
    }