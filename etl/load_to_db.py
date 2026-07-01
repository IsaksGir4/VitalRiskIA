# ============================================================
# VitalRisk AI — load_to_db.py
# Equipo 326 | Carga el Feature Store en PostGIS
# Orden obligatorio por dependencias FK (ADR 002, Sección 4)
# ============================================================

import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(Path(__file__).parent.parent / ".env")

# Agrega esto temporalmente justo después de load_dotenv() para debuggear
print(f"USER: {os.getenv('DB_USER')}")
print(f"PASS: {os.getenv('DB_PASSWORD')}")
print(f"NAME: {os.getenv('DB_NAME')}")

DB_URL = (
    f"postgresql://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@127.0.0.1:"
    f"{os.getenv('DB_PORT', '5433')}/"
    f"{os.getenv('DB_NAME')}"
)

engine = create_engine(DB_URL)


BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED = Path(__file__).parent.parent / "data" / "processed"


# ── Función auxiliar de carga con upsert ──────────────────
def cargar_tabla(df, tabla, llave_unica, engine, chunksize=500):
    """
    Inserta filas nuevas y actualiza las existentes (upsert).
    Usa la constraint UNIQUE definida en init.sql.
    """
    cols = ", ".join(df.columns)
    placeholders = ", ".join([f":{c}" for c in df.columns])
    updates = ", ".join([f"{c} = EXCLUDED.{c}" 
                         for c in df.columns if c not in llave_unica])
    
    sql = f"""
        INSERT INTO {tabla} ({cols})
        VALUES ({placeholders})
        ON CONFLICT ({", ".join(llave_unica)})
        DO UPDATE SET {updates}
    """
    
    with engine.begin() as conn:
        registros = df.to_dict(orient="records")
        for i in range(0, len(registros), chunksize):
            chunk = registros[i:i+chunksize]
            conn.execute(text(sql), chunk)
    
    print(f"  ✓ {tabla}: {len(df):,} filas cargadas")

# ── 1. dim_municipios (primero — todas las FK dependen de esto) ──
print("\n[1/5] Cargando dim_municipios...")
gdf = gpd.read_file(PROCESSED / "clean_municipios.geojson")

# Preparar columnas que coinciden con init.sql v4
COLS_MUNI = [
    'codigo_dane', 'nombre', 'departamento',
    'icv_score', 'nbi', 'ipm_pct',
    'icv_hacinamiento', 'icv_menores_6', 'icv_seg_social',
    'pct_vivienda_acueducto', 'icv_paredes', 'icv_pisos',
    'subregion', 'poblacion_2023'
]
df_muni = pd.DataFrame(gdf[COLS_MUNI]).copy()
# df_muni['subregion'] = df_muni['codigo_dane'].apply(
#     lambda x: 'Valle de Aburrá' if x in {
#         '05001','05088','05129','05212','05266',
#         '05308','05360','05380','05631','05837'
#     } else 'Resto de Antioquia'
# )
df_muni['poblacion_2023'] = df_muni['poblacion_2023'].astype('Int64')

# Cargar geometría por separado (requiere GeoAlchemy2)
from geoalchemy2 import Geometry, WKTElement
gdf_geo = gdf[['codigo_dane', 'geometry']].copy()
gdf_geo['geometria'] = gdf_geo['geometry'].apply(
    lambda g: WKTElement(g.wkt, srid=4326)
)

# Carga sin geometría primero
cargar_tabla(df_muni, 'dim_municipios', ['codigo_dane'], engine)

# Actualizar geometría
with engine.begin() as conn:
    for _, row in gdf_geo.iterrows():
        conn.execute(text("""
            UPDATE dim_municipios 
            SET geometria = ST_Multi(ST_GeomFromText(:wkt, 4326))
            WHERE codigo_dane = :cod
        """), {"wkt": row['geometry'].wkt, "cod": row['codigo_dane']})
print("  ✓ dim_municipios: geometrías actualizadas")

# ── 2. dim_poblacion_anual ─────────────────────────────────
print("\n[2/5] Cargando dim_poblacion_anual...")
df_pob = pd.read_csv(PROCESSED / "clean_poblacion_anual.csv",
                     dtype={'codigo_dane': str})
df_pob['codigo_dane'] = df_pob['codigo_dane'].str.zfill(5)
df_pob['poblacion_total'] = df_pob['poblacion_total'].astype(int)
cargar_tabla(df_pob, 'dim_poblacion_anual', 
             ['codigo_dane', 'anio'], engine)

# ── 3. fact_calidad_aire ───────────────────────────────────
print("\n[3/5] Cargando fact_calidad_aire...")
df_clima = pd.read_csv(PROCESSED / "clean_calidad_aire.csv",
                       dtype={'codigo_dane': str})
df_clima['codigo_dane'] = df_clima['codigo_dane'].str.zfill(5)

COLS_CLIMA_BD = [
    'codigo_dane', 'anio', 'semana_epi',
    'pm25_avg', 'pm10_avg', 'temperatura_avg',
    'humedad_avg', 'precipitacion_sum', 'presion_avg', 'fuente_pm'
]
df_clima_bd = df_clima[COLS_CLIMA_BD].copy()
cargar_tabla(df_clima_bd, 'fact_calidad_aire',
             ['codigo_dane', 'anio', 'semana_epi'], engine)

# ── 4. fact_eventos_ira ────────────────────────────────────
print("\n[4/5] Cargando fact_eventos_ira...")
df_ira = pd.read_csv(PROCESSED / "clean_ira_2018_2023.csv",
                     dtype={'codigo_dane': str})
df_ira['codigo_dane'] = df_ira['codigo_dane'].str.zfill(5)

# Excluir código inválido (documentado en NB04)
df_ira = df_ira[df_ira['codigo_dane'] != '05000'].copy()

COLS_IRA_BD = [
    'codigo_dane', 'anio', 'semana_epi', 'fecha_semana',
    'casos_ira_total', 'edad_promedio', 'rezago_reporte_dias',
    'pct_regimen_contributivo', 'pct_regimen_especial_excepcion',
    'pct_regimen_otros', 'pct_regimen_subsidiado',
    'periodo_pandemia'
]
cols_ok = [c for c in COLS_IRA_BD if c in df_ira.columns]
cargar_tabla(df_ira[cols_ok], 'fact_eventos_ira',
             ['codigo_dane', 'anio', 'semana_epi'], engine)

# ── 5. fact_riesgo_territorial ─────────────────────────────
print("\n[5/5] Cargando fact_riesgo_territorial...")
df_feat = pd.read_csv(PROCESSED / "fact_riesgo_territorial.csv",
                      dtype={'codigo_dane': str})
df_feat['codigo_dane'] = df_feat['codigo_dane'].str.zfill(5)


# ipt_score y nivel_riesgo se cargan como NULL (se calculan en HU11)
df_feat['ipt_score']   = None
df_feat['nivel_riesgo'] = None
# Antes de cargar fact_riesgo_territorial
df_feat['casos_ira_lag1'] = df_feat['casos_ira_lag1'].astype('Int64')  # Int64 soporta NA
df_feat['casos_ira_total'] = df_feat['casos_ira_total'].astype('Int64')

# Reemplazar nan por None para que PostgreSQL los reciba como NULL
df_feat = df_feat.where(pd.notna(df_feat), other=None)

COLS_FEAT_BD = [
    'codigo_dane', 'anio', 'semana_epi', 'fecha_semana',
    'casos_ira_total', 'tasa_ira_100k',
    'pm25_avg', 'pm10_avg', 'temperatura_avg', 'humedad_avg',
    'precipitacion_sum', 'presion_avg', 'fuente_pm',
    'pm25_lag1', 'pm25_lag2', 'casos_ira_lag1',
    'icv_score', 'nbi', 'ipm_pct', 'icv_hacinamiento',
    'icv_menores_6', 'icv_seg_social', 'pct_vivienda_acueducto',
    'icv_paredes', 'icv_pisos',
    'edad_promedio', 'rezago_reporte_dias',
    'pct_regimen_contributivo', 'pct_regimen_especial_excepcion',
    'pct_regimen_otros', 'pct_regimen_subsidiado',
    'periodo_pandemia', 'ipt_score', 'nivel_riesgo'
]
cols_ok = [c for c in COLS_FEAT_BD if c in df_feat.columns]
cargar_tabla(df_feat[cols_ok], 'fact_riesgo_territorial',
             ['codigo_dane', 'anio', 'semana_epi'], engine)

# ── Verificación final ─────────────────────────────────────
print("\n=== VERIFICACIÓN FINAL EN POSTGIS ===")
with engine.connect() as conn:
    tablas = ['dim_municipios', 'dim_poblacion_anual',
              'fact_calidad_aire', 'fact_eventos_ira',
              'fact_riesgo_territorial']
    for t in tablas:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"  {t}: {n:,} filas")