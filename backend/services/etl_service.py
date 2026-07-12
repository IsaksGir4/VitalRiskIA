"""
ETL Service v2 — Pipeline Near-Real-Time para VitalRisk AI
============================================================
Extrae datos climáticos + PM2.5 de APIs Socrata, calcula IPT real,
ejecuta XGBoost, genera alertas.

5 fuentes Socrata (datos.gov.co):
  - Humedad:       uext-mhny  (IDEAM)
  - Temperatura:   sbwg-7ju4  (IDEAM)
  - Precipitación: s54a-sgyg  (IDEAM)
  - Presión:       62tk-nxj5  (IDEAM)
  - PM2.5/PM10:    g4t8-zkc3  (SISAIRE) ← NUEVO

Equipo 326 | Datos al Ecosistema 2026
"""

import math
import unicodedata
import numpy as np
import pandas as pd
import requests as http_requests
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from scipy.stats import rankdata

from services.ml_service import MLService
from services.alertas_service import AlertasService

SOCRATA_BASE = "https://www.datos.gov.co/resource"
SOCRATA_TIMEOUT = 30
SOCRATA_LIMIT = 50000

# 4 datasets IDEAM (mismas columnas: municipio, fechaobservacion, valorobservado)
DATASETS_IDEAM = {
    "humedad_avg":       "uext-mhny",
    "temperatura_avg":   "sbwg-7ju4",
    "precipitacion_sum": "s54a-sgyg",
    "presion_avg":       "62tk-nxj5",
}

# SISAIRE PM2.5 (columnas diferentes: codigo_municipio, med_fecha_inicio, etc.)
SISAIRE_ID = "g4t8-zkc3"


def _semana_epi(fecha: datetime) -> tuple[int, int]:
    iso = fecha.isocalendar()
    return iso[0], iso[1]


def _fecha_inicio_semana(anio: int, semana: int) -> str:
    from datetime import date
    return date.fromisocalendar(anio, semana, 1).isoformat()


def _safe_db(value):
    if value is None:
        return None
    try:
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


class ETLService:

    # ══════════════════════════════════════════════════════
    # FASE 0: MAPEOS
    # ══════════════════════════════════════════════════════

    @staticmethod
    def build_nombre_to_dane(db: Session) -> dict:
        rows = db.execute(text(
            "SELECT codigo_dane, nombre FROM dim_municipios"
        )).fetchall()
        mapping = {}
        for row in rows:
            cod = str(row.codigo_dane).zfill(5)
            nombre = row.nombre.upper().strip()
            mapping[nombre] = cod
            nfkd = unicodedata.normalize('NFKD', nombre)
            sin_tildes = ''.join(c for c in nfkd if not unicodedata.combining(c))
            mapping[sin_tildes] = cod
        return mapping

    @staticmethod
    def get_poblacion(db: Session, codigo_dane: str, anio: int) -> int:
        """Obtiene población proyectada DANE para el año dado."""
        row = db.execute(text(
            "SELECT poblacion_total FROM dim_poblacion_anual "
            "WHERE codigo_dane = :cod AND anio = :a"
        ), {"cod": codigo_dane, "a": anio}).fetchone()
        if row:
            return int(row.poblacion_total)
        # Fallback: año más cercano disponible
        row = db.execute(text(
            "SELECT poblacion_total FROM dim_poblacion_anual "
            "WHERE codigo_dane = :cod ORDER BY ABS(anio - :a) LIMIT 1"
        ), {"cod": codigo_dane, "a": anio}).fetchone()
        return int(row.poblacion_total) if row else 50000

    # ══════════════════════════════════════════════════════
    # FASE 1: EXTRACT
    # ══════════════════════════════════════════════════════

    @staticmethod
    def fetch_ideam(dataset_id: str, fecha_desde: str, fecha_hasta: str) -> pd.DataFrame:
        """Extrae de IDEAM (4 datasets clima). Campo clave: municipio (texto)."""
        url = f"{SOCRATA_BASE}/{dataset_id}.json"
        params = {
            "$where": (f"departamento='ANTIOQUIA' AND "
                       f"fechaobservacion >= '{fecha_desde}T00:00:00.000' AND "
                       f"fechaobservacion <= '{fecha_hasta}T23:59:59.000'"),
            "$select": "municipio, fechaobservacion, valorobservado",
            "$limit": SOCRATA_LIMIT,
            "$order": "fechaobservacion DESC",
        }
        try:
            r = http_requests.get(url, params=params, timeout=SOCRATA_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if not data:
                    return pd.DataFrame()
                df = pd.DataFrame(data)
                df["valor"] = pd.to_numeric(df["valorobservado"], errors="coerce")
                df["fechaobservacion"] = pd.to_datetime(df["fechaobservacion"], errors="coerce")
                df["municipio"] = df["municipio"].str.upper().str.strip()
                return df.dropna(subset=["valor", "fechaobservacion"])
            else:
                print(f"    ⚠ HTTP {r.status_code}: {r.text[:200]}")
                return pd.DataFrame()
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return pd.DataFrame()

    @staticmethod
    def fetch_sisaire_pm25(fecha_desde: str, fecha_hasta: str) -> pd.DataFrame:
        """
        Extrae PM2.5 de SISAIRE (g4t8-zkc3).
        Campos clave: codigo_municipio (DANE directo), msfl_code, med_concentracion_estandar
        """
        url = f"{SOCRATA_BASE}/{SISAIRE_ID}.json"
        params = {
            "$where": (f"codigo_departamento = 5 AND "
                       f"msfl_code = 'PM2.5' AND "
                       f"med_fecha_inicio >= '{fecha_desde}T00:00:00.000' AND "
                       f"med_fecha_inicio <= '{fecha_hasta}T23:59:59.000'"),
            "$select": "codigo_municipio, med_fecha_inicio, med_concentracion_estandar",
            "$limit": SOCRATA_LIMIT,
            "$order": "med_fecha_inicio DESC",
        }
        try:
            r = http_requests.get(url, params=params, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if not data:
                    print(f"    PM2.5: 0 registros. Intentando sin filtro de fecha...")
                    # Fallback: últimos datos disponibles
                    params2 = {
                        "$where": ("codigo_departamento = 5 AND msfl_code = 'PM2.5' AND "
                                   "med_fecha_inicio >= '2024-06-01T00:00:00.000'"),
                        "$select": "codigo_municipio, med_fecha_inicio, med_concentracion_estandar",
                        "$limit": SOCRATA_LIMIT,
                        "$order": "med_fecha_inicio DESC",
                    }

                    r2 = http_requests.get(url, params=params2, timeout=60)
                    if r2.status_code == 200:
                        data = r2.json()
                    else:
                        return pd.DataFrame()

                if not data:
                    return pd.DataFrame()

                df = pd.DataFrame(data)
                df["valor"] = pd.to_numeric(df["med_concentracion_estandar"], errors="coerce")
                df["fechaobservacion"] = pd.to_datetime(df["med_fecha_inicio"], errors="coerce")
                df["codigo_dane"] = df["codigo_municipio"].astype(str).str.zfill(5)
                return df.dropna(subset=["valor", "fechaobservacion"])
            else:
                print(f"    ⚠ SISAIRE HTTP {r.status_code}: {r.text[:200]}")
                return pd.DataFrame()
        except Exception as e:
            print(f"    ✗ Error SISAIRE: {e}")
            return pd.DataFrame()

    # ══════════════════════════════════════════════════════
    # FASE 2: TRANSFORM
    # ══════════════════════════════════════════════════════

    @classmethod
    def transform_clima_semanal(
        cls, datos_ideam: dict[str, pd.DataFrame], nombre_to_dane: dict
    ) -> pd.DataFrame:
        """Agrega IDEAM diario → semanal por municipio."""
        dfs = []
        for variable, df_raw in datos_ideam.items():
            if df_raw.empty:
                continue
            df = df_raw.copy()
            s = df["fechaobservacion"].apply(_semana_epi)
            df["anio"] = s.apply(lambda x: x[0])
            df["semana_epi"] = s.apply(lambda x: x[1])
            df["codigo_dane"] = df["municipio"].map(nombre_to_dane)
            df = df.dropna(subset=["codigo_dane"])

            agg = "sum" if "precipitacion" in variable else "mean"
            df_agg = df.groupby(["codigo_dane", "anio", "semana_epi"])["valor"].agg(agg).reset_index()
            df_agg.rename(columns={"valor": variable}, inplace=True)
            dfs.append(df_agg)
            print(f"  ✓ {variable}: {len(df_agg)} filas")

        if not dfs:
            return pd.DataFrame()
        result = dfs[0]
        for d in dfs[1:]:
            result = result.merge(d, on=["codigo_dane", "anio", "semana_epi"], how="outer")
        return result

    @classmethod
    def transform_pm25_semanal(cls, df_pm25: pd.DataFrame) -> pd.DataFrame:
        """Agrega SISAIRE PM2.5 como promedio por municipio (dato más reciente disponible)."""
        if df_pm25.empty:
            return pd.DataFrame()
        # SISAIRE tiene rezago — calculamos promedio por municipio, no por semana
        df_agg = df_pm25.groupby("codigo_dane")["valor"].mean().reset_index()
        df_agg.rename(columns={"valor": "pm25_avg"}, inplace=True)
        print(f"  ✓ pm25_avg (SISAIRE): {len(df_agg)} municipios con promedio PM2.5")
        return df_agg

    @classmethod
    def calcular_ipt(cls, row, all_values: dict) -> float:
        """
        Calcula IPT con fórmula real:
        0.40 × percentil(tasa_ira) + 0.30 × percentil(pm25) +
        0.15 × percentil(ipm) + 0.15 × percentil(hacinamiento)
        Resultado escalado a 0-100.
        """
        tasa = row.get("tasa_ira_100k", 0) or 0
        pm25 = row.get("pm25_avg", 0) or 0
        ipm = row.get("ipm_pct", 0) or 0
        hac = row.get("icv_hacinamiento", 0) or 0

        # Percentiles simples (posición relativa en los datos actuales)
        def pct(val, vals_list):
            if not vals_list or len(vals_list) < 2:
                return 0.5
            arr = np.array(vals_list)
            return np.sum(arr <= val) / len(arr)

        z_tasa = pct(tasa, all_values.get("tasa", []))
        z_pm25 = pct(pm25, all_values.get("pm25", []))
        z_ipm = pct(ipm, all_values.get("ipm", []))
        z_hac = pct(hac, all_values.get("hac", []))

        ipt_raw = 0.40 * z_tasa + 0.30 * z_pm25 + 0.15 * z_ipm + 0.15 * z_hac
        return round(np.clip(ipt_raw * 100, 0, 100), 2)

    @classmethod
    def enrich_features(cls, df_semanal: pd.DataFrame, db: Session) -> pd.DataFrame:
        """Enriquece con lags, socioeconómicos, población, IPT."""
        if df_semanal.empty:
            return df_semanal

        # Socioeconómicos
        socio = pd.read_sql(text(
            "SELECT codigo_dane, icv_score, nbi, ipm_pct, "
            "icv_hacinamiento, icv_seg_social FROM dim_municipios"
        ), db.bind)
        df = df_semanal.merge(socio, on="codigo_dane", how="left")

        # Lags + media histórica + población
        for idx, row in df.iterrows():
            cod = row["codigo_dane"]
            anio = int(row["anio"])
            sem = int(row["semana_epi"])

            # Población proyectada DANE
            pob = cls.get_poblacion(db, cod, anio)
            df.at[idx, "poblacion_total"] = pob

            # Semana anterior
            sem_p, anio_p = (sem - 1, anio) if sem > 1 else (52, anio - 1)
            prev = db.execute(text(
                "SELECT casos_ira_total, pm25_avg FROM fact_riesgo_territorial "
                "WHERE codigo_dane = :c AND anio = :a AND semana_epi = :s"
            ), {"c": cod, "a": anio_p, "s": sem_p}).fetchone()

            df.at[idx, "casos_ira_lag1"] = float(prev.casos_ira_total) if prev and prev.casos_ira_total else None
            df.at[idx, "pm25_lag1"] = float(prev.pm25_avg) if prev and prev.pm25_avg else None

            # Media histórica (sin pandemia)
            m = db.execute(text(
                "SELECT AVG(casos_ira_total) AS media FROM fact_riesgo_territorial "
                "WHERE codigo_dane = :c AND semana_epi = :s "
                "AND anio BETWEEN 2018 AND 2023 AND periodo_pandemia = FALSE"
            ), {"c": cod, "s": sem}).fetchone()
            media = float(m.media) if m and m.media else 3.0
            df.at[idx, "casos_ira_total"] = media
            df.at[idx, "media_hist_mun_sem"] = media

            # tasa_ira_100k con población proyectada
            df.at[idx, "tasa_ira_100k"] = (media / pob * 100000) if pob > 0 else 0

        # Estacionalidad
        df["semana_sin"] = np.sin(2 * np.pi * df["semana_epi"] / 52)
        df["semana_cos"] = np.cos(2 * np.pi * df["semana_epi"] / 52)
        df["desviacion_vs_historico"] = df.apply(
            lambda r: ((r["casos_ira_total"] - r["media_hist_mun_sem"])
                       / r["media_hist_mun_sem"] * 100
                       if r["media_hist_mun_sem"] > 0 else 0.0), axis=1)

        # IPT real con percentiles
        all_vals = {
            "tasa": df["tasa_ira_100k"].dropna().tolist(),
            "pm25": df["pm25_avg"].dropna().tolist() if "pm25_avg" in df.columns else [],
            "ipm": df["ipm_pct"].dropna().tolist(),
            "hac": df["icv_hacinamiento"].dropna().tolist(),
        }
        df["ipt_score"] = df.apply(lambda r: cls.calcular_ipt(r, all_vals), axis=1)
        df["nivel_riesgo"] = df["ipt_score"].apply(
            lambda x: "BAJO" if x < 33 else "ALTO" if x >= 66 else "MEDIO"
        )

        if "pm25_avg" not in df.columns:
            df["pm25_avg"] = None

        return df

    # ══════════════════════════════════════════════════════
    # FASE 3: LOAD + PREDICT
    # ══════════════════════════════════════════════════════

    @classmethod
    def predict_and_store(cls, df: pd.DataFrame, db: Session) -> dict:
        ml = MLService.get_instance()
        if ml.modelo is None:
            return {"status": "error", "mensaje": "Modelo no disponible"}

        stats = {"municipios_procesados": 0,
                 "alertas_generadas": {"VERDE": 0, "NARANJA": 0, "ROJA": 0},
                 "errores": 0}

        for _, row in df.iterrows():
            try:
                cod = row["codigo_dane"]
                anio, sem = int(row["anio"]), int(row["semana_epi"])

                fv = {k: row.get(k) for k in [
                    "casos_ira_total", "casos_ira_lag1", "pm25_avg", "pm25_lag1",
                    "humedad_avg", "icv_seg_social", "icv_score", "ipm_pct",
                    "media_hist_mun_sem", "desviacion_vs_historico",
                    "semana_sin", "semana_cos"
                ]}

                pred, var_causal = ml.predict(fv)
                if math.isnan(pred) or math.isinf(pred):
                    pred = 0.0

                media = row.get("media_hist_mun_sem", 3.0)
                nivel, desv = AlertasService.calcular_nivel_alerta(pred, media)

                # UPSERT fact_riesgo_territorial
                db.execute(text("""
                    INSERT INTO fact_riesgo_territorial
                        (codigo_dane, anio, semana_epi, fecha_semana,
                         casos_ira_total, tasa_ira_100k, pm25_avg,
                         temperatura_avg, humedad_avg, precipitacion_sum,
                         presion_avg, pm25_lag1, casos_ira_lag1,
                         icv_score, nbi, ipm_pct, icv_hacinamiento,
                         icv_seg_social, periodo_pandemia,
                         ipt_score, nivel_riesgo)
                    VALUES (:cod, :anio, :sem, :fecha,
                            :casos, :tasa, :pm25, :temp, :hum, :prec,
                            :pres, :pm25l, :casosl, :icv, :nbi, :ipm,
                            :hac, :seg, FALSE, :ipt, :nivel_r)
                    ON CONFLICT (codigo_dane, anio, semana_epi) DO UPDATE SET
                        casos_ira_total = COALESCE(EXCLUDED.casos_ira_total, fact_riesgo_territorial.casos_ira_total),
                        tasa_ira_100k = COALESCE(EXCLUDED.tasa_ira_100k, fact_riesgo_territorial.tasa_ira_100k),
                        pm25_avg = COALESCE(EXCLUDED.pm25_avg, fact_riesgo_territorial.pm25_avg),
                        temperatura_avg = COALESCE(EXCLUDED.temperatura_avg, fact_riesgo_territorial.temperatura_avg),
                        humedad_avg = COALESCE(EXCLUDED.humedad_avg, fact_riesgo_territorial.humedad_avg),
                        precipitacion_sum = COALESCE(EXCLUDED.precipitacion_sum, fact_riesgo_territorial.precipitacion_sum),
                        presion_avg = COALESCE(EXCLUDED.presion_avg, fact_riesgo_territorial.presion_avg),
                        pm25_lag1 = COALESCE(EXCLUDED.pm25_lag1, fact_riesgo_territorial.pm25_lag1),
                        casos_ira_lag1 = COALESCE(EXCLUDED.casos_ira_lag1, fact_riesgo_territorial.casos_ira_lag1),
                        ipt_score = EXCLUDED.ipt_score,
                        nivel_riesgo = EXCLUDED.nivel_riesgo
                """), {
                    "cod": cod, "anio": anio, "sem": sem,
                    "fecha": _fecha_inicio_semana(anio, sem),
                    "casos": _safe_db(row.get("casos_ira_total")),
                    "tasa": _safe_db(row.get("tasa_ira_100k")),
                    "pm25": _safe_db(row.get("pm25_avg")),
                    "temp": _safe_db(row.get("temperatura_avg")),
                    "hum": _safe_db(row.get("humedad_avg")),
                    "prec": _safe_db(row.get("precipitacion_sum")),
                    "pres": _safe_db(row.get("presion_avg")),
                    "pm25l": _safe_db(row.get("pm25_lag1")),
                    "casosl": _safe_db(row.get("casos_ira_lag1")),
                    "icv": _safe_db(row.get("icv_score")),
                    "nbi": _safe_db(row.get("nbi")),
                    "ipm": _safe_db(row.get("ipm_pct")),
                    "hac": _safe_db(row.get("icv_hacinamiento")),
                    "seg": _safe_db(row.get("icv_seg_social")),
                    "ipt": _safe_db(row.get("ipt_score")),
                    "nivel_r": row.get("nivel_riesgo", "MEDIO"),
                })

                # UPSERT alertas_territoriales
                db.execute(text("""
                    INSERT INTO alertas_territoriales
                        (codigo_dane, anio, semana_epi, nivel_alerta,
                         prediccion_casos, media_historica, desviacion_pct,
                         variable_causal, activa)
                    VALUES (:cod, :anio, :sem, :nivel, :pred, :media,
                            :desv, :var, TRUE)
                    ON CONFLICT (codigo_dane, anio, semana_epi) DO UPDATE SET
                        nivel_alerta = EXCLUDED.nivel_alerta,
                        prediccion_casos = EXCLUDED.prediccion_casos,
                        media_historica = EXCLUDED.media_historica,
                        desviacion_pct = EXCLUDED.desviacion_pct,
                        variable_causal = EXCLUDED.variable_causal,
                        fecha_generacion = NOW(), activa = TRUE
                """), {
                    "cod": cod, "anio": anio, "sem": sem,
                    "nivel": nivel, "pred": round(pred, 2),
                    "media": round(media, 2), "desv": round(desv, 2),
                    "var": var_causal,
                })

                stats["municipios_procesados"] += 1
                k = nivel.replace("ALERTA_", "")
                stats["alertas_generadas"][k] = stats["alertas_generadas"].get(k, 0) + 1

            except Exception as e:
                print(f"  ✗ Error {row.get('codigo_dane')}: {e}")
                stats["errores"] += 1

        db.commit()
        return stats

    # ══════════════════════════════════════════════════════
    # ORQUESTADOR
    # ══════════════════════════════════════════════════════

    @classmethod
    def ejecutar_pipeline(cls, db: Session, dias_atras: int = 14,
                          semana_override: Optional[int] = None,
                          anio_override: Optional[int] = None) -> dict:
        print("=" * 60)
        print("VitalRisk AI — ETL Pipeline v2 (con PM2.5 SISAIRE)")
        print("=" * 60)

        ahora = datetime.now()
        anio_t, sem_t = (anio_override, semana_override) if (anio_override and semana_override) else _semana_epi(ahora)
        f_desde = (ahora - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
        f_hasta = ahora.strftime("%Y-%m-%d")

        print(f"  Objetivo: {anio_t}-W{sem_t:02d} | Rango: {f_desde} → {f_hasta}\n")

        # FASE 0
        print("── FASE 0: MAPEO ──")
        n2d = cls.build_nombre_to_dane(db)
        print(f"  {len(n2d)} nombres→DANE\n")

        # FASE 1
        print("── FASE 1: EXTRACT ──")
        datos_ideam = {}
        for var, did in DATASETS_IDEAM.items():
            print(f"  → {var} ({did})...")
            datos_ideam[var] = cls.fetch_ideam(did, f_desde, f_hasta)
            print(f"    {len(datos_ideam[var])} registros")

        print(f"  → pm25_avg SISAIRE ({SISAIRE_ID})...")
        df_pm25 = cls.fetch_sisaire_pm25(f_desde, f_hasta)
        print(f"    {len(df_pm25)} registros PM2.5")

        total = sum(len(d) for d in datos_ideam.values()) + len(df_pm25)
        if total == 0:
            return {"status": "sin_datos", "semana": f"{anio_t}-W{sem_t:02d}",
                    "mensaje": "Sin datos en Socrata para ese rango"}
        print(f"\n  Total extraído: {total}\n")

        # FASE 2
        print("── FASE 2: TRANSFORM ──")
        df_clima = cls.transform_clima_semanal(datos_ideam, n2d)
        df_pm = cls.transform_pm25_semanal(df_pm25)

        # Merge clima + PM2.5 (PM2.5 es promedio municipal, no semanal)
        if not df_clima.empty:
            df_all = df_clima.copy()
            if not df_pm.empty:
                df_all = df_all.merge(df_pm, on="codigo_dane", how="left")
        elif not df_pm.empty:
            df_all = df_pm
        else:
            return {"status": "sin_datos_transformados", "mensaje": "No se mapearon datos"}

        # Filtrar semana objetivo
        df_all = df_all.sort_values(["anio", "semana_epi"], ascending=False)
        if semana_override:
            df_t = df_all[(df_all["anio"] == anio_t) & (df_all["semana_epi"] == sem_t)]
            if df_t.empty:
                u = df_all.iloc[0]
                df_t = df_all[(df_all["anio"] == u["anio"]) & (df_all["semana_epi"] == u["semana_epi"])]
                print(f"  ⚠ W{sem_t} no disponible. Usando {int(u['anio'])}-W{int(u['semana_epi'])}")
        else:
            u = df_all.iloc[0]
            df_t = df_all[(df_all["anio"] == u["anio"]) & (df_all["semana_epi"] == u["semana_epi"])]
            print(f"  Semana más reciente: {int(u['anio'])}-W{int(u['semana_epi']):02d}")

        print(f"  Municipios: {len(df_t)}")

        print("  Enriqueciendo features + IPT...")
        df_final = cls.enrich_features(df_t.copy(), db)
        print(f"  {len(df_final)} municipios listos\n")

        # FASE 3
        print("── FASE 3: PREDICT + STORE ──")
        stats = cls.predict_and_store(df_final, db)

        resultado = {
            "status": "success",
            "semana": f"{anio_t}-W{sem_t:02d}",
            "rango": f"{f_desde} → {f_hasta}",
            "registros_socrata": total,
            "municipios": stats["municipios_procesados"],
            "alertas": stats["alertas_generadas"],
            "errores": stats["errores"],
            "fuentes": {
                "ideam_humedad": len(datos_ideam.get("humedad_avg", [])),
                "ideam_temperatura": len(datos_ideam.get("temperatura_avg", [])),
                "ideam_precipitacion": len(datos_ideam.get("precipitacion_sum", [])),
                "ideam_presion": len(datos_ideam.get("presion_avg", [])),
                "sisaire_pm25": len(df_pm25),
            },
            "timestamp": ahora.isoformat(),
        }
        print(f"\n  ✓ {stats['municipios_procesados']} municipios | Alertas: {stats['alertas_generadas']}")
        print("=" * 60)
        return resultado