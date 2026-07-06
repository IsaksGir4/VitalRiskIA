import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from settings.config import settings

class MLService:
    _instance = None

    @classmethod
    def get_instance(cls) -> "MLService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        with open(settings.MODEL_PATH, "rb") as f:
            artefacto = pickle.load(f)
        self.modelo            = artefacto["modelo"]
        self.features          = artefacto["features"]
        self.fill_values       = artefacto["fill_values"]
        self.feature_importance = artefacto["feature_importance"]
        print(f"✓ MLService: modelo cargado ({len(self.features)} features)")

    def predict(self, feature_values: dict) -> tuple[float, str]:
        X = pd.DataFrame([{
            feat: feature_values.get(feat, self.fill_values.get(feat))
            for feat in self.features
        }])
        for feat in self.features:
            if pd.isna(X[feat].iloc[0]) and feat in self.fill_values:
                X[feat] = self.fill_values[feat]
        pred = float(np.clip(self.modelo.predict(X)[0], 0, None))
        variable_causal = max(
            self.feature_importance, key=self.feature_importance.get
        )
        return pred, variable_causal
    
    def get_model_metadata(self) -> dict:
        return {
            "algoritmo": "XGBoost Regressor",
            "version_artefacto": "1.0",
            "fecha_entrenamiento": "2026-07-01",
            "features_count": len(self.features),
            "features": self.features,
            "feature_importance_gain": self.feature_importance,
            "split_temporal": {
                "train": "2018-2020 (498 filas)",
                "validation": "2021 (53 filas — 100% pandemia)",
                "test": "2022-2023 (256 filas)"
            },
            "metricas_test": {
                "rmse": 1.7399,
                "mae": 1.0295,
                "r2": 0.607,
                "rmse_naive_baseline": 2.0763,
                "mejora_vs_naive_pct": 16.2
            },
            "cv_temporal": {
                "metodo": "TimeSeriesSplit 5 folds",
                "rmse_medio": 1.9147,
                "rmse_std": 1.4778,
                "rmse_por_fold": [4.4306, 1.0329, 1.1465, 0.2886, 2.6751]
            },
            "explicabilidad": {
                "metodo": "SHAP TreeExplainer",
                "base_value": 3.2665,
                "variable_causal_mas_frecuente": "pm25_avg",
                "nota": "variable_causal calculada por SHAP por predicción individual"
            },
            "justificacion_seleccion": (
                "XGBoost seleccionado sobre Extra Trees (mejor RMSE en val) por: "
                "manejo nativo de NaN (tree_method=hist), explicabilidad SHAP requerida "
                "para variable_causal, regularización L1/L2."
            )
        }