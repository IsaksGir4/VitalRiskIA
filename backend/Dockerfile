# ============================================================
# VitalRisk AI — Dockerfile Backend (FastAPI + XGBoost)
# Equipo 326 | Datos al Ecosistema 2026
# Deploy: Render Web Service
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# Dependencias de sistema para psycopg2 y compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python primero (capa cacheada)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY backend/ .

# Copiar artefactos de modelo y datos necesarios en runtime
COPY data/models/ /app/data/models/
COPY data/processed/clean_municipios.geojson /app/data/processed/clean_municipios.geojson

EXPOSE 8000

# Sin --reload en producción
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]