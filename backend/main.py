# Codigo minimo de FastAPI(Walking Skeleton)
from fastapi import FastAPI

app = FastAPI(
    title="VitalRisk AI - API",
    description="API para vigilancia preventiva territorial",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    """
    Endpoint de verificación de estado.
    Cumple con el criterio de aceptación de la HU 1.1.
    """
    return {"status": "OK", "message": "API de VitalRisk AI funcionando correctamente"}