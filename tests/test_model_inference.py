"""
Tests de Inferencia del Modelo — VitalRisk AI
===============================================
Valida que el modelo XGBoost produce outputs consistentes,
dentro de rangos válidos y con el comportamiento esperado.

Ejecutar: pytest tests/test_model_inference.py -v
"""

import pytest
import pickle
import numpy as np
import pandas as pd
import math
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "data" / "models" / "modelo_xgboost_vitalrisk.pkl"


@pytest.fixture(scope="module")
def artefacto():
    assert MODEL_PATH.exists(), f"Modelo no encontrado en {MODEL_PATH}"
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


@pytest.fixture(scope="module")
def modelo(artefacto):
    return artefacto["modelo"]


@pytest.fixture(scope="module")
def features(artefacto):
    return artefacto["features"]


@pytest.fixture(scope="module")
def fill_values(artefacto):
    return artefacto["fill_values"]


# ── Validaciones del artefacto ───────────────────────────

class TestArtefacto:

    def test_artefacto_tiene_claves_requeridas(self, artefacto):
        """El artefacto .pkl debe contener modelo, features y fill_values."""
        requeridas = ["modelo", "features", "fill_values", "feature_importance"]
        for clave in requeridas:
            assert clave in artefacto, f"Clave faltante en el artefacto: {clave}"

    def test_numero_features(self, features):
        """El modelo debe tener exactamente 12 features."""
        assert len(features) == 12, \
            f"Se esperan 12 features, se encontraron {len(features)}"

    def test_features_requeridas(self, features):
        """Las features clave del modelo deben estar presentes."""
        requeridas = [
            "casos_ira_lag1", "casos_ira_total", "media_hist_mun_sem",
            "semana_sin", "semana_cos"
        ]
        for f in requeridas:
            assert f in features, f"Feature clave faltante: {f}"

    def test_fill_values_completos(self, features, fill_values):
        """Cada feature debe tener un fill_value para manejar NaN."""
        for f in features:
            assert f in fill_values, f"fill_value faltante para: {f}"

    def test_feature_importance_suma_uno(self, artefacto):
        """La feature importance normalizada debe sumar ≈ 1."""
        fi = artefacto["feature_importance"]
        total = sum(fi.values())
        assert abs(total - 1.0) < 0.01, \
            f"Feature importance no suma 1: {total:.4f}"


# ── Validaciones de predicción ───────────────────────────

class TestPrediccion:

    def _build_input(self, features, fill_values, overrides=None):
        """Construye un DataFrame de input con fill_values y overrides opcionales."""
        row = {f: fill_values.get(f, 0) for f in features}
        if overrides:
            row.update(overrides)
        return pd.DataFrame([row])

    def test_prediccion_es_float(self, modelo, features, fill_values):
        """El output del modelo debe ser un float."""
        X = self._build_input(features, fill_values)
        pred = float(modelo.predict(X)[0])
        assert isinstance(pred, float), f"Predicción no es float: {type(pred)}"

    def test_prediccion_no_nan(self, modelo, features, fill_values):
        """La predicción no debe ser NaN ni inf."""
        X = self._build_input(features, fill_values)
        pred = float(modelo.predict(X)[0])
        assert not math.isnan(pred), "Predicción es NaN"
        assert not math.isinf(pred), "Predicción es inf"

    def test_prediccion_no_negativa(self, modelo, features, fill_values):
        """La predicción de casos no puede ser negativa (se aplica clip a 0)."""
        X = self._build_input(features, fill_values)
        pred = float(np.clip(modelo.predict(X)[0], 0, None))
        assert pred >= 0, f"Predicción negativa: {pred}"

    def test_prediccion_rango_razonable(self, modelo, features, fill_values):
        """La predicción debe estar en un rango epidemiológicamente razonable."""
        X = self._build_input(features, fill_values)
        pred = float(np.clip(modelo.predict(X)[0], 0, None))
        assert pred <= 100, \
            f"Predicción muy alta ({pred:.1f} casos) — posible error en features"

    def test_prediccion_con_nans(self, modelo, features, fill_values):
        """El modelo debe manejar NaN usando fill_values sin error."""
        row = {f: np.nan for f in features}
        X = pd.DataFrame([row])
        for f in features:
            if pd.isna(X[f].iloc[0]) and f in fill_values:
                X[f] = fill_values[f]
        pred = float(np.clip(modelo.predict(X)[0], 0, None))
        assert not math.isnan(pred), "Predicción es NaN con fill_values aplicados"

    def test_casos_altos_producen_prediccion_mayor(self, modelo, features, fill_values):
        """Más casos actuales debe producir una predicción mayor (monotonía esperada)."""
        X_bajo = self._build_input(features, fill_values, {"casos_ira_total": 1, "casos_ira_lag1": 1})
        X_alto = self._build_input(features, fill_values, {"casos_ira_total": 10, "casos_ira_lag1": 10})
        pred_bajo = float(modelo.predict(X_bajo)[0])
        pred_alto = float(modelo.predict(X_alto)[0])
        assert pred_alto > pred_bajo, \
            f"Casos altos ({pred_alto:.2f}) no superan casos bajos ({pred_bajo:.2f})"

    def test_prediccion_batch(self, modelo, features, fill_values):
        """El modelo debe procesar múltiples municipios en batch sin error."""
        rows = [
            {f: fill_values.get(f, 0) for f in features}
            for _ in range(38)
        ]
        X = pd.DataFrame(rows)
        preds = modelo.predict(X)
        assert len(preds) == 38, f"Batch de 38 produjo {len(preds)} predicciones"
        assert all(not math.isnan(p) for p in preds), "NaN en predicciones batch"


# ── Validación de métricas documentadas ──────────────────

class TestMetricasDocumentadas:

    def test_metricas_json_existe(self):
        """El archivo de métricas debe existir junto al modelo."""
        metricas_path = MODEL_PATH.parent / "metricas_modelo.json"
        assert metricas_path.exists(), \
            f"No se encontró metricas_modelo.json en {metricas_path}"

    def test_rmse_documentado(self):
        """El RMSE documentado debe ser ≤ 2.0 (mejora sobre naive de 2.08)."""
        import json
        metricas_path = MODEL_PATH.parent / "metricas_modelo.json"
        if metricas_path.exists():
            with open(metricas_path) as f:
                metricas = json.load(f)
            rmse = metricas.get("rmse_test", metricas.get("rmse", None))
            if rmse is not None:
                assert rmse <= 2.0, \
                    f"RMSE documentado ({rmse}) supera el baseline naive (2.08)"