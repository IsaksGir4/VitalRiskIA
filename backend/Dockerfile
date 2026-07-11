# Instrucciones para construir el contenedor de la API
FROM python:3.10-slim

# Establecer el directorio de trabajo principal
WORKDIR /app

# 1. Copiar los requirements desde la carpeta backend
COPY requirements.txt .

# 2. Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copiar TODO el repositorio (Esto incluye 'backend/' y 'models/')
COPY . .

# 4. Cambiar el directorio de trabajo específicamente a backend para correr uvicorn
WORKDIR /app

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicación (sin --reload para producción)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]