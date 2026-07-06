import math
import unicodedata


def safe_float(value) -> float | None:
    """Convierte a float seguro para JSON. Retorna None si es NaN o inf."""
    if value is None:
        return None
    try:
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None

def safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
    
def normalizar_texto(texto: str) -> str:
    """Elimina tildes y caracteres especiales para compatibilidad CSV/Excel."""
    if not texto:
        return texto
    # Descompone caracteres acentuados y elimina los diacríticos
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return ''.join(c for c in nfkd if not unicodedata.combining(c))