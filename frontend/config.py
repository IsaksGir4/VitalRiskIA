import os
import requests

# Lee la URL de la API desde las variables de entorno, o usa localhost si falla (para desarrollo)
API = os.getenv("VITALRISK_API_URL", "http://localhost:8000")

# Cuando llames a un endpoint:
respuesta = requests.get(f"{API}/api/v1/mapa/riesgo")