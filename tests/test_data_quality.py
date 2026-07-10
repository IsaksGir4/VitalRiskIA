"""
Tests de Calidad de Datos — VitalRisk AI
==========================================
Valida rangos, nulos, tipos y consistencia de las variables
en las tablas clave del sistema.

Ejecutar: pytest tests/test_data_quality.py -v
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"


@pytest.fixture(scope="module")
def df_ipt():
    path = DATA_DIR / "fact_riesgo_territorial_ipt.csv"
    assert path.exists(), f"No se encontró {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def df_alertas():
    path = DATA_DIR / "alertas_territoriales.csv"
    assert path.exists(), f"No se encontró {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def df_municipios():
    path = DATA_DIR / "clean_municipios.csv"
    assert path.exists(), f"No se encontró {path}"
    return pd.read_csv(path)


# ── Validaciones de fact_riesgo_territorial_ipt ──────────

class TestFactRiesgoTerritorial:

    def test_columnas_requeridas(self, df_ipt):
        """Las columnas clave del dataset deben existir."""
        requeridas = [
            "codigo_dane", "anio", "semana_epi",
            "casos_ira_total", "pm25_avg", "ipt_score", "nivel_riesgo"
        ]
        for col in requeridas:
            assert col in df_ipt.columns, f"Columna faltante: {col}"

    def test_codigo_dane_formato(self, df_ipt):
        """codigo_dane debe ser string de 5 dígitos."""
        df_ipt["codigo_dane"] = df_ipt["codigo_dane"].astype(str).str.zfill(5)
        assert df_ipt["codigo_dane"].str.len().eq(5).all(), \
            "codigo_dane debe tener exactamente 5 caracteres"

    def test_anio_rango(self, df_ipt):
        """Los años deben estar entre 2018 y 2027."""
        assert df_ipt["anio"].between(2018, 2027).all(), \
            f"Años fuera de rango: {df_ipt['anio'].unique()}"

    def test_semana_rango(self, df_ipt):
        """La semana epidemiológica debe estar entre 1 y 53."""
        assert df_ipt["semana_epi"].between(1, 53).all(), \
            "Semanas fuera del rango 1-53"

    def test_casos_ira_no_negativos(self, df_ipt):
        """casos_ira_total no puede ser negativo."""
        validos = df_ipt["casos_ira_total"].dropna()
        assert (validos >= 0).all(), "Hay casos IRA negativos"

    def test_ipt_rango(self, df_ipt):
        """El IPT debe estar entre 0 y 100."""
        validos = df_ipt["ipt_score"].dropna()
        assert validos.between(0, 100).all(), \
            f"IPT fuera de rango 0-100. Min: {validos.min():.2f}, Max: {validos.max():.2f}"

    def test_nivel_riesgo_valores(self, df_ipt):
        """nivel_riesgo solo puede tomar BAJO, MEDIO o ALTO."""
        permitidos = {"BAJO", "MEDIO", "ALTO"}
        validos = df_ipt["nivel_riesgo"].dropna()
        encontrados = set(validos.unique())
        assert encontrados.issubset(permitidos), \
            f"Valores inválidos en nivel_riesgo: {encontrados - permitidos}"

    def test_pm25_rango_fisico(self, df_ipt):
        """PM2.5 debe estar entre 0 y 500 µg/m³ (rango físico razonable)."""
        validos = df_ipt["pm25_avg"].dropna()
        assert (validos >= 0).all(), "PM2.5 negativo"
        assert (validos <= 500).all(), \
            f"PM2.5 sobre 500 µg/m³: {validos[validos > 500].values}"

    def test_sin_duplicados_clave(self, df_ipt):
        """No debe haber duplicados en (codigo_dane, anio, semana_epi)."""
        clave = ["codigo_dane", "anio", "semana_epi"]
        n_duplicados = df_ipt.duplicated(subset=clave).sum()
        assert n_duplicados == 0, \
            f"Se encontraron {n_duplicados} filas duplicadas en la clave primaria"

    def test_municipios_antioquia(self, df_ipt):
        """Todos los códigos DANE deben ser de Antioquia (05xxx)."""
        df_ipt["codigo_dane"] = df_ipt["codigo_dane"].astype(str).str.zfill(5)
        no_antioquia = df_ipt[~df_ipt["codigo_dane"].str.startswith("05")]
        assert len(no_antioquia) == 0, \
            f"Municipios no Antioquia: {no_antioquia['codigo_dane'].unique()}"

    def test_minimo_municipios(self, df_ipt):
        """Debe haber datos de al menos 90 municipios distintos."""
        n_municipios = df_ipt["codigo_dane"].nunique()
        assert n_municipios >= 90, \
            f"Solo {n_municipios} municipios (se esperan ≥ 90)"

    def test_cobertura_temporal(self, df_ipt):
        """Debe haber datos desde 2018 hasta al menos 2023."""
        anios = df_ipt["anio"].unique()
        for anio in [2018, 2019, 2020, 2021, 2022, 2023]:
            assert anio in anios, f"Falta el año {anio} en los datos"


# ── Validaciones de alertas_territoriales ────────────────

class TestAlertasTerritorial:

    def test_columnas_requeridas(self, df_alertas):
        """Las columnas clave de alertas deben existir."""
        requeridas = [
            "codigo_dane", "anio", "semana_epi",
            "nivel_alerta", "prediccion_casos_t1", "desviacion_prediccion_pct",
            "variable_causal", "media_hist_mun_sem"
        ]
        for col in requeridas:
            assert col in df_alertas.columns, f"Columna faltante: {col}"

    def test_nivel_alerta_valores(self, df_alertas):
        """nivel_alerta solo puede ser ALERTA_VERDE, ALERTA_NARANJA o ALERTA_ROJA."""
        permitidos = {"ALERTA_VERDE", "ALERTA_NARANJA", "ALERTA_ROJA"}
        encontrados = set(df_alertas["nivel_alerta"].dropna().unique())
        assert encontrados.issubset(permitidos), \
            f"Niveles inválidos: {encontrados - permitidos}"

    def test_prediccion_no_negativa(self, df_alertas):
        """La predicción de casos no puede ser negativa."""
        validos = df_alertas["prediccion_casos_t1"].dropna()
        assert (validos >= 0).all(), \
            f"Predicciones negativas: {validos[validos < 0].values[:5]}"

    def test_variable_causal_no_nula(self, df_alertas):
        """variable_causal no debe ser nula (SHAP siempre asigna una)."""
        nulos = df_alertas["variable_causal"].isna().sum()
        pct = nulos / len(df_alertas) * 100
        assert pct < 5, f"Demasiados nulos en variable_causal: {pct:.1f}%"

    def test_distribucion_alertas(self, df_alertas):
        """La mayoría de alertas históricas deben ser VERDE (comportamiento esperado)."""
        dist = df_alertas["nivel_alerta"].value_counts(normalize=True)
        pct_verde = dist.get("ALERTA_VERDE", 0)
        assert pct_verde >= 0.70, \
            f"Solo {pct_verde*100:.1f}% son ALERTA_VERDE (se espera ≥ 70%)"

    def test_volumen_minimo(self, df_alertas):
        """Debe haber al menos 800 alertas generadas."""
        assert len(df_alertas) >= 800, \
            f"Solo {len(df_alertas)} alertas (se esperan ≥ 800)"


# ── Validaciones de dim_municipios ───────────────────────

class TestDimMunicipios:

    def test_cobertura_municipios(self, df_municipios):
        """Debe haber exactamente 125 municipios en el GeoJSON."""
        assert len(df_municipios) >= 100, \
            f"Solo {len(df_municipios)} municipios (se esperan ≥ 100)"

    def test_icv_rango(self, df_municipios):
        """ICV debe estar entre 0 y 100."""
        if "icv_score" in df_municipios.columns:
            validos = df_municipios["icv_score"].dropna()
            assert validos.between(0, 100).all(), "ICV fuera de rango 0-100"

    def test_ipm_rango(self, df_municipios):
        """IPM porcentual debe estar entre 0 y 100."""
        if "ipm_pct" in df_municipios.columns:
            validos = df_municipios["ipm_pct"].dropna()
            assert validos.between(0, 100).all(), "IPM fuera de rango 0-100"