# ============================================================
# VitalRisk AI — Dockerfile Frontend (Streamlit)
# Equipo 326 | Datos al Ecosistema 2026
# Deploy: Render Web Service
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# Dependencias de sistema mínimas para Streamlit + Folium
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python primero (capa cacheada)
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del frontend
COPY frontend/ .

# GeoJSON base para el mapa coroplético
# IMPORTANTE: debe copiarse aquí porque en Render el frontend
# no tiene acceso al directorio raíz del proyecto.
# La ruta en dashboard.py es: Path(__file__).parent.parent / "data/processed/..."
COPY data/processed/clean_municipios_simple.geojson /app/data/processed/clean_municipios_simple.geojson

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]