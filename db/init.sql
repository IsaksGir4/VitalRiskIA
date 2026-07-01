-- ============================================================
-- VitalRisk AI — init.sql v4
-- Equipo 326 | Alineado con datos reales HU5-HU8 (junio 2026)
-- ============================================================
-- CAMBIOS RESPECTO A v3:
--   1. fact_calidad_aire: eliminado timestamp_medicion (no existe en el CSV
--      real — la granularidad es municipio-semana, no por estación).
--      El índice problemático sobre timestamp_medicion fue removido.
--   2. dim_estaciones_aire: se mantiene en el schema como reserva para
--      cuando lleguen datos del SIATA (radicado 021682), pero se documenta
--      que actualmente está vacía.
--   3. dim_municipios: agregadas columnas icv_paredes e icv_pisos
--      (extraídas de ECV Antioquia 2023 en NB03). Eliminada cobertura_salud
--      (no disponible en los datos reales procesados).
--   4. fact_eventos_ira: granularidad cambiada a municipio-semana (agregado),
--      no registro individual. Reflejado en columnas reales del NB01.
--   5. fact_riesgo_territorial: sin cambios estructurales.
--   6. alertas_territoriales: sin cambios estructurales.
-- ============================================================

-- 1. Extensión espacial
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- DIMENSIONES
-- ============================================================

-- 2. Municipios con geometría
--    Fuente: DANE MGN2025 (GeoJSON) + ECV Antioquia 2023 (indicadores)
--    Carga: ETL desde clean_municipios.geojson (NB03)
--    125 municipios de Antioquia — 10 del Valle de Aburrá como foco
CREATE TABLE IF NOT EXISTS dim_municipios (
    codigo_dane            VARCHAR(5)    PRIMARY KEY,
    nombre                 VARCHAR(100)  NOT NULL,
    departamento           VARCHAR(100)  NOT NULL,
    subregion              VARCHAR(100),
    -- Población base 2023 (para referencia rápida sin JOIN)
    poblacion_2023         INTEGER,
    -- Indicadores ECV Antioquia 2023 (features socioeconómicas invariantes)
    icv_score              NUMERIC(5,2), -- Indicador calidad de vida (0-100)
    icv_hacinamiento       NUMERIC(5,2), -- D4 V1 Hacinamiento (amplifica IRA)
    icv_menores_6          NUMERIC(5,2), -- D4 V2 % menores de 6 años (vulnerables)
    icv_seg_social         NUMERIC(5,2), -- D5 V2 Seg. social jefe de hogar
    icv_paredes            NUMERIC(5,2), -- D4 V3 Paredes no adecuadas
    icv_pisos              NUMERIC(5,2), -- D4 V4 Pisos no adecuados
    pct_vivienda_acueducto NUMERIC(5,2), -- % viviendas con acueducto
    nbi                    NUMERIC(5,2), -- NBI (Necesidades Básicas Insatisfechas)
    ipm_pct                NUMERIC(5,2), -- % pobreza multidimensional
    -- Geometría MultiPolygon (IGAC / MGN2025)
    geometria              GEOMETRY(MultiPolygon, 4326)
);

CREATE INDEX IF NOT EXISTS idx_municipios_geom
    ON dim_municipios USING GIST (geometria);

-- 3. Población anual
--    Fuente: DANE — Proyecciones CNPV 2018 (2018-2023)
--    Carga: ETL desde clean_poblacion_anual.csv (NB03)
--    Necesaria para calcular tasa_ira_100k con denominador correcto por año
CREATE TABLE IF NOT EXISTS dim_poblacion_anual (
    codigo_dane     VARCHAR(5)  REFERENCES dim_municipios(codigo_dane),
    anio            SMALLINT    NOT NULL,
    poblacion_total INTEGER     NOT NULL CHECK (poblacion_total > 0),
    -- Fuente: DANE proyecciones base CNPV 2018
    PRIMARY KEY (codigo_dane, anio)
);

-- 4. Estaciones de monitoreo de calidad del aire
--    ESTADO ACTUAL: tabla reservada — actualmente vacía.
--    Razón: los datos del IDEAM se agregaron directamente a nivel municipio-semana
--    en el NB02 (spatial join), sin conservar la granularidad por estación.
--    Se poblará cuando lleguen datos del SIATA (radicado 021682, pendiente).
CREATE TABLE IF NOT EXISTS dim_estaciones_aire (
    estacion_id    VARCHAR(30)   PRIMARY KEY,
    nombre         VARCHAR(150)  NOT NULL,
    fuente         VARCHAR(20)   NOT NULL, -- 'SIATA' | 'IDEAM'
    codigo_dane    VARCHAR(5)    REFERENCES dim_municipios(codigo_dane),
    latitud        NUMERIC(10,7) NOT NULL,
    longitud       NUMERIC(10,7) NOT NULL,
    altitud_msnm   INTEGER,
    activa         BOOLEAN       DEFAULT TRUE,
    ubicacion      GEOMETRY(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_estaciones_ubicacion
    ON dim_estaciones_aire USING GIST (ubicacion);

-- ============================================================
-- HECHOS
-- ============================================================

-- 5. Calidad del aire — semanal por municipio
--    Fuente primaria: SIATA (radicado 021682, pendiente)
--    Fuente secundaria: IDEAM — SISAIRE granulado (PM2.5/PM10 2020-2023)
--                               + DHIME (temperatura, humedad, prec., presión 2018-2023)
--    Granularidad: 1 fila por municipio × semana epidemiológica
--    Notas:
--      - PM2.5/PM10 2018-2019: imputados desde Promedio Anual (fuente_pm = 'IMPUTADO_PA')
--      - PM2.5/PM10 2020-2023: datos directos SISAIRE (fuente_pm = 'SISAIRE_DIRECTO')
--      - presion_avg: cobertura ~15% (pocas estaciones DHIME en Antioquia)
CREATE TABLE IF NOT EXISTS fact_calidad_aire (
    id                BIGSERIAL    PRIMARY KEY,
    codigo_dane       VARCHAR(5)   NOT NULL
                      REFERENCES dim_municipios(codigo_dane),
    anio              SMALLINT     NOT NULL,
    semana_epi        SMALLINT     NOT NULL
                      CHECK (semana_epi BETWEEN 1 AND 53),
    -- Contaminantes (µg/m³) — promedio semanal de todas las estaciones del municipio
    pm25_avg          NUMERIC(8,3),
    pm10_avg          NUMERIC(8,3),
    -- Variables meteorológicas semanales
    temperatura_avg   NUMERIC(5,2), -- °C, promedio semanal
    humedad_avg       NUMERIC(5,2), -- %, promedio semanal
    precipitacion_sum NUMERIC(8,2), -- mm, suma semanal
    presion_avg       NUMERIC(7,2), -- hPa, promedio semanal (baja cobertura)
    -- Trazabilidad del origen del dato de PM
    -- Valores: 'SISAIRE_DIRECTO' | 'IMPUTADO_PA' | NULL (sin dato PM)
    fuente_pm         VARCHAR(20),
    -- Unicidad: un municipio tiene un solo registro por semana/año
    UNIQUE (codigo_dane, anio, semana_epi)
);

CREATE INDEX IF NOT EXISTS idx_aire_municipio_semana
    ON fact_calidad_aire (codigo_dane, anio, semana_epi);

-- 6. Eventos IRA — agregados por municipio y semana epidemiológica
--    Fuente: INS / ESI-IRAG Vigilancia Centinela 2018-2023
--    Granularidad: 1 fila por municipio × semana × año
--    Notas:
--      - periodo_pandemia: TRUE para 2020-03-01 a 2021-12-31
--      - pct_regimen_*: distribución proporcional del régimen de salud (suman ~1.0)
--      - rezago_reporte_dias: diferencia fecha_inicio_sint - fecha_notificacion (mediana)
CREATE TABLE IF NOT EXISTS fact_eventos_ira (
    id                           BIGSERIAL    PRIMARY KEY,
    codigo_dane                  VARCHAR(5)   NOT NULL
                                 REFERENCES dim_municipios(codigo_dane),
    semana_epi                   SMALLINT     NOT NULL
                                 CHECK (semana_epi BETWEEN 1 AND 53),
    anio                         SMALLINT     NOT NULL,
    fecha_semana                 DATE,
    -- Variable objetivo del modelo de predicción
    casos_ira_total              INTEGER      NOT NULL CHECK (casos_ira_total >= 0),
    -- Covariables demográficas agregadas por semana
    edad_promedio                NUMERIC(5,2),
    rezago_reporte_dias          NUMERIC(5,2),
    -- Distribución del régimen de salud (proporciones, suman ~1.0)
    pct_regimen_contributivo     NUMERIC(5,4),
    pct_regimen_especial_excepcion NUMERIC(5,4),
    pct_regimen_otros            NUMERIC(5,4),
    pct_regimen_subsidiado       NUMERIC(5,4),
    -- Control metodológico
    periodo_pandemia             BOOLEAN      DEFAULT FALSE,
    fuente_dato                  VARCHAR(20)  DEFAULT 'ESI-IRAG',
    -- Unicidad
    UNIQUE (codigo_dane, anio, semana_epi)
);

CREATE INDEX IF NOT EXISTS idx_ira_municipio_semana
    ON fact_eventos_ira (codigo_dane, anio, semana_epi);

-- 7. Feature Store — tabla maestra analítica
--    Resultado del ETL HU7 + HU8 (NB04)
--    Granularidad: 1 fila por municipio × semana epidemiológica
--    Alimenta: HU9 (correlaciones), HU10 (winsorización), HU11 (IPT), HU12-13 (XGBoost)
--    Columnas ipt_score y nivel_riesgo: se calculan en HU11 y se actualizan con upsert
CREATE TABLE IF NOT EXISTS fact_riesgo_territorial (
    id                  BIGSERIAL    PRIMARY KEY,
    codigo_dane         VARCHAR(5)   REFERENCES dim_municipios(codigo_dane),
    semana_epi          SMALLINT     NOT NULL,
    anio                SMALLINT     NOT NULL,
    fecha_semana        DATE,

    -- === VARIABLE OBJETIVO ===
    casos_ira_total     INTEGER,
    tasa_ira_100k       NUMERIC(8,4),

    -- === FEATURES AMBIENTALES (promedio/suma semanal por municipio) ===
    pm25_avg            NUMERIC(8,3),
    pm10_avg            NUMERIC(8,3),
    temperatura_avg     NUMERIC(5,2),
    humedad_avg         NUMERIC(5,2),
    precipitacion_sum   NUMERIC(8,2),
    presion_avg         NUMERIC(7,2),
    fuente_pm           VARCHAR(20),  -- trazabilidad del origen de PM

    -- === FEATURES REZAGADAS (calculadas en HU7) ===
    pm25_lag1           NUMERIC(8,3), -- PM2.5 semana t-1 (exposición reciente)
    pm25_lag2           NUMERIC(8,3), -- PM2.5 semana t-2 (exposición acumulada)
    casos_ira_lag1      INTEGER,      -- Casos IRA semana t-1 (autocorrelación)

    -- === FEATURES SOCIOECONÓMICAS (invariantes — de dim_municipios) ===
    icv_score           NUMERIC(5,2),
    nbi                 NUMERIC(5,2),
    ipm_pct             NUMERIC(5,2),
    icv_hacinamiento    NUMERIC(5,2),
    icv_menores_6       NUMERIC(5,2),
    icv_seg_social      NUMERIC(5,2),
    pct_vivienda_acueducto NUMERIC(5,2),
    icv_paredes         NUMERIC(5,2),
    icv_pisos           NUMERIC(5,2),

    -- === COVARIABLES DEMOGRÁFICAS (de fact_eventos_ira) ===
    edad_promedio       NUMERIC(5,2),
    rezago_reporte_dias NUMERIC(5,2),
    pct_regimen_contributivo      NUMERIC(5,4),
    pct_regimen_especial_excepcion NUMERIC(5,4),
    pct_regimen_otros             NUMERIC(5,4),
    pct_regimen_subsidiado        NUMERIC(5,4),

    -- === CONTROL ===
    periodo_pandemia    BOOLEAN       DEFAULT FALSE,

    -- === IPT — calculado en HU11, actualizado con upsert ===
    ipt_score           NUMERIC(5,2)  CHECK (ipt_score >= 0 AND ipt_score <= 100),
    nivel_riesgo        VARCHAR(10)   CHECK (nivel_riesgo IN ('BAJO', 'MEDIO', 'ALTO')),

    -- Garantiza upsert sin duplicados (requerimiento HU8)
    UNIQUE (codigo_dane, anio, semana_epi)
);

CREATE INDEX IF NOT EXISTS idx_riesgo_municipio_semana
    ON fact_riesgo_territorial (codigo_dane, anio, semana_epi);

-- 8. Alertas territoriales — generadas por el motor XGBoost (HU15)
--    Se llena en la Épica 4, no en la 3.
--    Lógica: si prediccion_casos se desvía > umbral de media histórica → alerta.
--    Umbrales: VERDE <15% | NARANJA 15-30% | ROJA >30%
--    variable_causal: feature con mayor importancia en XGBoost para esa predicción
CREATE TABLE IF NOT EXISTS alertas_territoriales (
    id                BIGSERIAL    PRIMARY KEY,
    codigo_dane       VARCHAR(5)   REFERENCES dim_municipios(codigo_dane),
    semana_epi        SMALLINT     NOT NULL,
    anio              SMALLINT     NOT NULL,
    fecha_generacion  TIMESTAMPTZ  DEFAULT NOW(),
    nivel_alerta      VARCHAR(20)  CHECK (
                          nivel_alerta IN ('ALERTA_VERDE','ALERTA_NARANJA','ALERTA_ROJA')),
    prediccion_casos  NUMERIC(8,2),  -- salida del modelo XGBoost
    media_historica   NUMERIC(8,2),  -- promedio histórico mismo municipio-semana (sin pandemia)
    desviacion_pct    NUMERIC(6,2),  -- (prediccion - media) / media * 100
    variable_causal   VARCHAR(50),   -- feature más importante según XGBoost Feature Importance
    activa            BOOLEAN        DEFAULT TRUE
);

-- ============================================================
-- COMENTARIOS (visibles con \d+ en psql — útil para HU23)
-- ============================================================
COMMENT ON TABLE dim_municipios IS
    'Catálogo de 125 municipios de Antioquia con geometría PostGIS.
     Fuente: DANE MGN2025 + ECV Antioquia 2023. Índice foco: Valle de Aburrá (10 municipios).
     Poblar antes que cualquier tabla de hechos (restricciones FK).';

COMMENT ON TABLE dim_poblacion_anual IS
    'Proyecciones de población por municipio y año. Fuente: DANE base CNPV 2018 (2018-2023).
     Necesaria para calcular tasa_ira_100k con denominador correcto por año histórico.';

COMMENT ON TABLE dim_estaciones_aire IS
    'Catálogo de estaciones de monitoreo de calidad del aire.
     ESTADO: reservada — actualmente vacía. Se poblará con datos SIATA (radicado 021682).
     Fuente secundaria prevista: IDEAM dataset 57sv-p2fu.';

COMMENT ON TABLE fact_calidad_aire IS
    'Variables ambientales semanales por municipio. Granularidad: municipio × semana epi.
     PM 2020-2023: SISAIRE directo. PM 2018-2019: imputado desde Promedio Anual IDEAM.
     Meteorología: DHIME/IDEAM (temperatura sbwg-7ju4, precipitación s54a-sgyg,
     presión 62tk-nxj5, humedad uext-mhny).';

COMMENT ON TABLE fact_eventos_ira IS
    'Casos ESI-IRAG agregados por municipio × semana epidemiológica. Fuente: INS 2018-2023.
     Variable objetivo del modelo XGBoost. periodo_pandemia=TRUE: 2020-03 a 2021-12.';

COMMENT ON TABLE fact_riesgo_territorial IS
    'Feature Store: tabla maestra analítica. Resultado del ETL HU7+HU8.
     1 fila por municipio × semana epidemiológica. Llave: (codigo_dane, anio, semana_epi).
     ipt_score y nivel_riesgo: calculados en HU11, inicialmente NULL.';

COMMENT ON TABLE alertas_territoriales IS
    'Alertas generadas por motor XGBoost (HU15 — Épica 4).
     Niveles: VERDE (<15%) | NARANJA (15-30%) | ROJA (>30%) sobre media histórica.
     variable_causal: feature de mayor importancia en la predicción que activó la alerta.';