"""
VitalRisk AI — Tests de integración del backend (HU19)
Equipo 326 | Datos al Ecosistema 2026

Valida los endpoints críticos de la API FastAPI contra los criterios
de aceptación Gherkin del Scrum Master Data (Épica 6, HU19).

Ejecución:
    pytest tests/test_integration_api.py -v

Nota: estos tests usan el cliente de prueba de FastAPI (TestClient)
contra el backend en producción (Render). No requieren BD local.
Para tests con BD local, usar conftest.py con mock data.
"""

import pytest
import requests

# URL de producción — se puede sobrescribir con variable de entorno
API_BASE = "https://vitalriskia.onrender.com/api/v1"

# Municipio de prueba: Medellín (05001)
CODIGO_DANE_TEST = "05001"
ANIO_TEST = 2023
SEMANA_TEST = 27


class TestHealth:
    """
    Scenario: El sistema responde correctamente
    Given el backend desplegado en Render
    When se consulta GET /health/
    Then retorna status 200 con modelo XGBoost cargado
    """

    def test_health_retorna_200(self):
        r = requests.get(f"{API_BASE}/health/", timeout=90)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    def test_health_modelo_ok(self):
        r = requests.get(f"{API_BASE}/health/", timeout=90)
        data = r.json()
        assert data["dependencias"]["modelo_xgboost"] == "OK"
        assert data["dependencias"]["features_modelo"] == 12

    def test_health_base_datos_ok(self):
        r = requests.get(f"{API_BASE}/health/", timeout=90)
        data = r.json()
        assert data["dependencias"]["base_de_datos"] == "OK"


class TestMapaRiesgo:
    """
    Scenario: Validación del endpoint geoespacial (criterio principal HU19)
    Given el cliente configurado contra la API de producción
    When se ejecuta GET /mapa/riesgo
    Then status 200 + Content-Type application/json
    And estructura GeoJSON FeatureCollection válida
    And cada feature tiene codigo_dane, ipt_score, nivel_riesgo
    """

    def test_mapa_riesgo_retorna_200(self):
        r = requests.get(
            f"{API_BASE}/mapa/riesgo",
            params={"anio": ANIO_TEST, "semana_epi": SEMANA_TEST},
            timeout=90,
        )
        assert r.status_code == 200

    def test_mapa_riesgo_content_type_json(self):
        r = requests.get(
            f"{API_BASE}/mapa/riesgo",
            params={"anio": ANIO_TEST, "semana_epi": SEMANA_TEST},
            timeout=90,
        )
        assert "application/json" in r.headers.get("Content-Type", "")

    def test_mapa_riesgo_es_geojson_feature_collection(self):
        r = requests.get(
            f"{API_BASE}/mapa/riesgo",
            params={"anio": ANIO_TEST, "semana_epi": SEMANA_TEST},
            timeout=90,
        )
        data = r.json()
        assert data.get("type") == "FeatureCollection", (
            f"Se esperaba 'FeatureCollection', se obtuvo '{data.get('type')}'"
        )
        assert "features" in data
        assert isinstance(data["features"], list)
        assert len(data["features"]) > 0, "La respuesta no tiene features"

    def test_mapa_riesgo_features_tienen_propiedades_requeridas(self):
        r = requests.get(
            f"{API_BASE}/mapa/riesgo",
            params={"anio": ANIO_TEST, "semana_epi": SEMANA_TEST},
            timeout=90,
        )
        data = r.json()
        for feature in data["features"][:5]:  # verificar las primeras 5
            props = feature.get("properties", {})
            assert "codigo_dane" in props, "Falta codigo_dane en properties"
            assert "ipt_score" in props, "Falta ipt_score en properties"
            assert "nivel_riesgo" in props, "Falta nivel_riesgo en properties"

    def test_mapa_riesgo_ipt_score_en_rango_valido(self):
        r = requests.get(
            f"{API_BASE}/mapa/riesgo",
            params={"anio": ANIO_TEST, "semana_epi": SEMANA_TEST},
            timeout=90,
        )
        data = r.json()
        for feature in data["features"]:
            ipt = feature["properties"].get("ipt_score")
            if ipt is not None:
                assert 0 <= ipt <= 100, f"IPT fuera de rango [0,100]: {ipt}"

    def test_mapa_riesgo_nivel_riesgo_valores_validos(self):
        r = requests.get(
            f"{API_BASE}/mapa/riesgo",
            params={"anio": ANIO_TEST, "semana_epi": SEMANA_TEST},
            timeout=90,
        )
        data = r.json()
        niveles_validos = {"BAJO", "MEDIO", "ALTO", None}
        for feature in data["features"]:
            nivel = feature["properties"].get("nivel_riesgo")
            assert nivel in niveles_validos, (
                f"nivel_riesgo inválido: '{nivel}'. "
                f"Debe ser uno de {niveles_validos}"
            )


class TestAlertas:
    """
    Scenario: Endpoint de alertas activas retorna estructura correcta
    """

    def test_alertas_activas_retorna_200(self):
        r = requests.get(f"{API_BASE}/alertas/activas", timeout=90)
        assert r.status_code == 200

    def test_alertas_activas_tiene_clave_alertas(self):
        r = requests.get(f"{API_BASE}/alertas/activas", timeout=90)
        data = r.json()
        # La API retorna {"alertas": [...], "total": N, "metadata": {...}}
        # no una lista directa — ajustado al contrato real del endpoint
        assert "alertas" in data, (
            f"Falta clave 'alertas'. Claves recibidas: {list(data.keys())}"
        )
        assert "total" in data
        assert isinstance(data["alertas"], list)

    def test_alertas_nivel_valores_validos(self):
        r = requests.get(f"{API_BASE}/alertas/activas", timeout=90)
        data = r.json()
        niveles_validos = {"ALERTA_VERDE", "ALERTA_NARANJA", "ALERTA_ROJA"}
        for alerta in data["alertas"]:  # extraer lista desde la clave correcta
            nivel = alerta.get("nivel_alerta", "")
            assert nivel in niveles_validos, (
                f"nivel_alerta invalido: '{nivel}'"
            )


class TestUltimaFecha:
    """
    Scenario: El sistema retorna la última semana disponible
    """

    def test_ultima_fecha_retorna_200(self):
        r = requests.get(f"{API_BASE}/mapa/ultima_fecha", timeout=90)
        assert r.status_code == 200

    def test_ultima_fecha_tiene_anio_y_semana(self):
        r = requests.get(f"{API_BASE}/mapa/ultima_fecha", timeout=90)
        data = r.json()
        assert "anio" in data
        assert "semana_epi" in data
        assert data["anio"] >= 2018
        assert 1 <= data["semana_epi"] <= 53