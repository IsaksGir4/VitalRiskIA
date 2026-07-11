# Instrucciones para construir el contenedor de la API
FROM python:3.10-slim

# Establecer el directorio de trabajo principal
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# 1. Copiar los requirements desde la carpeta backend
COPY backend/requirements.txt .

# 2. Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copiar el código de la API
COPY backend/ .
COPY data/models/ /app/data/models/
COPY data/processed/clean_municipios.geojson /app/data/processed/clean_municipios.geojson

# 4. Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicación (sin --reload para producción)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]