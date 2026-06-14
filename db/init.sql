-- ============================================================
-- VitalRisk AI — init.sql
-- Equipo 326 | Actualizado con base en datasets reales
-- ============================================================

-- 1. Extensión espacial
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- DIMENSIONES (catálogos de referencia, se cargan una vez)
-- ============================================================

-- 2. Municipios con geometría
--    Fuente: DANE DIVIPOLA + GeoJSON IGAC
--    Carga: ETL desde GeoJSON oficial del DANE
CREATE TABLE IF NOT EXISTS dim_municipios (
    codigo_dane     VARCHAR(5)   PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL,
    departamento    VARCHAR(100) NOT NULL,
    -- Subregión de Antioquia (ej. 'Valle de Aburrá', 'Oriente')
    -- Fuente: clasificación Gobernación de Antioquia
    subregion       VARCHAR(100),
    -- Proyecciones DANE CNPV 2018 — necesario para calcular tasas por 100k hab
    poblacion_2023  INTEGER,
    -- NBI: Índice de Necesidades Básicas Insatisfechas
    -- Fuente: DANE CNPV 2018 (archivo CNPV-2018-NBI.xlsx)
    nbi             NUMERIC(5,2),
    -- % afiliación al Sistema General de Seguridad Social en Salud
    -- Fuente: Gobernación de Antioquia / DSSA
    cobertura_salud NUMERIC(5,2),
    -- Agregar en dim_municipios después de cobertura_salud:
    icv_score           NUMERIC(5,2),
    -- Indicador de calidad de vida ECV 2023 (0-100), más actualizado que NBI
    -- Fuente: ECV Antioquia 2023, indicador 'Indicador de calidad de vida - ICV'

    icv_hacinamiento    NUMERIC(5,2),
    -- D4 V1 Hacinamiento — amplifica contagio de IRA en hogares
    -- Fuente: ECV Antioquia 2023

    icv_menores_6       NUMERIC(5,2),
    -- D4 V2 Proporción de menores de 6 años — grupo etario más vulnerable a IRA
    -- Fuente: ECV Antioquia 2023

    icv_seg_social      NUMERIC(5,2),
    -- D5 V2 Seguridad social jefe del hogar — proxy de cobertura en salud
    -- Fuente: ECV Antioquia 2023

    pct_vivienda_acueducto NUMERIC(5,2),
    -- % viviendas con acueducto — saneamiento básico, factor de riesgo IRA
    -- Fuente: ECV Antioquia 2023, Vivienda

    ipm_pct             NUMERIC(5,2),
    -- % personas pobres IPM — pobreza multidimensional
    -- Fuente: ECV Antioquia 2023
    geometria       GEOMETRY(MultiPolygon, 4326)
);

CREATE INDEX IF NOT EXISTS idx_municipios_geom
    ON dim_municipios USING GIST (geometria);

-- 3. Estaciones de monitoreo de calidad del aire
--    Fuente: SIATA (22 estaciones automáticas Valle de Aburrá)
--            IDEAM (dataset 57sv-p2fu en datos.gov.co)
--    Por qué existe: los datos ambientales vienen por estación,
--    no por municipio. Este catálogo permite el cruce estación → municipio.
CREATE TABLE IF NOT EXISTS dim_estaciones_aire (
    estacion_id     VARCHAR(30)  PRIMARY KEY,
    nombre          VARCHAR(150) NOT NULL,
    -- 'SIATA' | 'IDEAM' — para saber cuál pipeline los generó
    fuente          VARCHAR(20)  NOT NULL,
    codigo_dane     VARCHAR(5)   REFERENCES dim_municipios(codigo_dane),
    latitud         NUMERIC(10,7) NOT NULL,
    longitud        NUMERIC(10,7) NOT NULL,
    altitud_msnm  INTEGER,
-- Desnormalizado desde dim_estaciones_aire para no requerir JOIN en el EDA
    activa          BOOLEAN      DEFAULT TRUE,
    -- Punto geográfico para calcular municipio más cercano (Voronoi/Kriging)
    ubicacion       GEOMETRY(Point, 4326)
);


-- Después de dim_estaciones_aire:
CREATE TABLE IF NOT EXISTS dim_poblacion_anual (
    codigo_dane     VARCHAR(5)   REFERENCES dim_municipios(codigo_dane),
    anio            SMALLINT     NOT NULL,
    poblacion_total INTEGER      NOT NULL,
    -- Desagregación por sexo (disponible en proyecciones DANE)
    poblacion_hombres INTEGER,
    poblacion_mujeres INTEGER,
    -- Fuente: DANE — Proyecciones de población base CNPV 2018
    PRIMARY KEY (codigo_dane, anio)
);

CREATE INDEX IF NOT EXISTS idx_estaciones_ubicacion
    ON dim_estaciones_aire USING GIST (ubicacion);







-- ============================================================



-- HECHOS (mediciones y eventos — se actualizan con el ETL)



-- ============================================================

-- 4. Mediciones de calidad del aire
--    Granularidad: UNA fila por estación por timestamp
--    Fuente primaria: SIATA (histórico por solicitud, radicado 021682)
--    Fuente secundaria: IDEAM datasets g4t8-zkc3 y kekd-7v7h (datos.gov.co)
--    IMPORTANTE: no tiene UNIQUE por municipio/fecha porque una misma
--    ciudad puede tener varias estaciones midiendo al mismo tiempo.
CREATE TABLE IF NOT EXISTS fact_calidad_aire (
    id                  BIGSERIAL    PRIMARY KEY,
    estacion_id         VARCHAR(30)  REFERENCES dim_estaciones_aire(estacion_id),
    -- codigo_dane se desnormaliza aquí para acelerar el JOIN con IRA
    codigo_dane         VARCHAR(5)   REFERENCES dim_municipios(codigo_dane),
    -- Timestamp exacto de la medición (el SIATA reporta cada hora)
    timestamp_medicion  TIMESTAMPTZ  NOT NULL,
    -- Semana epidemiológica calculada en el ETL para facilitar el JOIN con IRA
    -- Rango válido: 1-52 (o 53 en años bisiestos)
    semana_epi          SMALLINT,
    anio                SMALLINT     NOT NULL,
    -- Contaminantes en µg/m³
    -- OMS: límite anual PM2.5 = 5 µg/m³; límite diario = 15 µg/m³
    pm25_ugm3           NUMERIC(8,3),
    pm10_ugm3           NUMERIC(8,3),
    -- Variables meteorológicas de control (afectan dispersión del PM2.5)
    temperatura_c       NUMERIC(5,2),
    humedad_relativa    NUMERIC(5,2),
    precipitacion_mm    NUMERIC(6,2),
    -- Para rastrear si el dato vino del SIATA o del IDEAM
    -- Agregar en fact_calidad_aire después de precipitacion_mm:
    presion_hpa         NUMERIC(7,2),
    -- Presión atmosférica en hPa
    -- Fuente: IDEAM dataset 62tk-nxj5
    -- La presión afecta la concentración de contaminantes a nivel del suelo
    -- Desnormalizado para evitar JOIN en el EDA
    altitud_estacion_m  SMALLINT,
    fuente_dato         VARCHAR(20)  NOT NULL
);

-- Índice compuesto para el JOIN más frecuente: municipio + semana
CREATE INDEX IF NOT EXISTS idx_aire_municipio_semana
    ON fact_calidad_aire (codigo_dane, anio, semana_epi);

CREATE INDEX IF NOT EXISTS idx_calidad_aire_timestamp 
    ON fact_calidad_aire (timestamp_medicion DESC);

-- 5. Eventos epidemiológicos IRA — nivel INDIVIDUAL (datos crudos SIVIGILA)
--    Granularidad: UNA fila por caso notificado
--    Fuente: INS / SIVIGILA — dataset individual de eventos
--    Por qué individual y no agregado: necesitamos edad, sexo y CIE-10
--    para las covariables del modelo. El GROUP BY se hace en el ETL (HU7).
CREATE TABLE IF NOT EXISTS fact_eventos_ira (
    id                  BIGSERIAL    PRIMARY KEY,
    codigo_dane         VARCHAR(5)   REFERENCES dim_municipios(codigo_dane),
    semana_epi          SMALLINT NOT NULL CHECK (semana_epi BETWEEN 1 AND 53),
    anio                SMALLINT     NOT NULL,
    fecha_inicio_sint   DATE,
    fecha_notificacion  DATE,
    -- Código CIE-10 del evento respiratorio
    -- Rango objetivo: J00 (resfriado común) a J22 (IRA baja no especificada)
    -- También incluye J44 (EPOC) y J45 (asma) para el módulo cardiovascular
    codigo_cie10        VARCHAR(10),
    -- Atributos demográficos — covariables del modelo
    edad_paciente       SMALLINT CHECK (edad_paciente >= 0 AND edad_paciente <= 120),
    -- 'M' | 'F' | 'I' (indeterminado, como aparece en el SIVIGILA)
    sexo                CHAR(1) CHECK (sexo IN ('M', 'F', 'I')),
    -- Subsidiado | Contributivo | Vinculado | No asegurado
    regimen_salud       VARCHAR(30),
    -- TRUE para registros entre 2020-03-01 y 2021-12-31
    -- Columna requerida por HU6 para el manejo del período COVID
    periodo_pandemia    BOOLEAN      DEFAULT FALSE,
    fuente_dato         VARCHAR(20)  DEFAULT 'SIVIGILA',
    -- En fact_eventos_ira, después de fuente_dato:
    cod_evento_sivigila  VARCHAR(10),
    -- Código del evento en el catálogo INS (ej. IRA = 345)
    -- Fuente: tabla de referencia SIVIGILA en portalsivigila.ins.gov.co
    -- Agregar en fact_eventos_ira:
    fuente_secundaria   VARCHAR(50),
    -- NULL para SIVIGILA puro
    -- 'METROSALUD' para registros de la ESE
    -- 'ENVIGADO_SP' para eventos de salud pública Envigado

    comuna_barrio       VARCHAR(100)
    -- Solo para registros de Metrosalud (latitud/longitud a nivel barrio)
    -- NULL para el resto
);


-- Índice para el GROUP BY del ETL (HU7)
CREATE INDEX IF NOT EXISTS idx_ira_municipio_semana
    ON fact_eventos_ira (codigo_dane, anio, semana_epi);

-- 6. Tabla maestra analítica — Feature Store
--    Granularidad: UNA fila por municipio por semana epidemiológica
--    Esta tabla es el RESULTADO del ETL (HU7 + HU8).
--    La llave es (codigo_dane, anio, semana_epi) — igual que IRA,
--    porque el cruce se hace a nivel semanal, no diario.
--    El UNIQUE garantiza el comportamiento de upsert en HU8.
CREATE TABLE IF NOT EXISTS fact_riesgo_territorial (
    id                  BIGSERIAL    PRIMARY KEY,
    codigo_dane         VARCHAR(5)   REFERENCES dim_municipios(codigo_dane),
    semana_epi          SMALLINT     NOT NULL,
    anio                SMALLINT     NOT NULL,

    -- === FEATURES AMBIENTALES (promedio semanal por municipio) ===
    -- Promediadas desde fact_calidad_aire agrupando por municipio+semana
    pm25_avg            NUMERIC(8,3),
    pm10_avg            NUMERIC(8,3),
    temperatura_avg     NUMERIC(5,2),
    humedad_avg         NUMERIC(5,2),
    precipitacion_sum   NUMERIC(8,2),
    -- Para saber si el PM2.5 es medición directa o interpolado
    -- (relevante para municipios sin estación propia — HU7)
    fuente_pm25         VARCHAR(30),

    -- === FEATURES REZAGADAS (lag variables — requeridas por HU12) ===
    -- PM2.5 de las 2 semanas previas (exposición acumulada)
    pm25_lag1           NUMERIC(8,3),
    pm25_lag2           NUMERIC(8,3),
    -- Casos IRA de la semana previa (autocorrelación de la serie)
    casos_ira_lag1      INTEGER,

    -- === VARIABLE OBJETIVO ===
    -- Resultado del GROUP BY sobre fact_eventos_ira
    casos_ira_total     INTEGER,
    -- Tasa por 100,000 hab (requiere poblacion_2023 de dim_municipios)
    tasa_ira_100k       NUMERIC(8,4),

    -- === IPT (resultado de HU11) ===
    ipt_score           NUMERIC(5,2) CHECK (ipt_score >= 0 AND ipt_score <= 100),  -- Acotado: 0 <= IPT <= 100
    -- 'BAJO' | 'MEDIO' | 'ALTO'
    nivel_riesgo       VARCHAR(10) CHECK (nivel_riesgo IN ('BAJO', 'MEDIO', 'ALTO')),

    -- === CONTROL ===
    periodo_pandemia    BOOLEAN        DEFAULT FALSE,

    -- Garantiza upsert sin duplicados (requerimiento HU8)
    UNIQUE (codigo_dane, anio, semana_epi)
);


CREATE INDEX IF NOT EXISTS idx_riesgo_municipio_semana
    ON fact_riesgo_territorial (codigo_dane, anio, semana_epi);

-- 7. Alertas del motor de ML
--    Generadas por HU15 cuando la predicción supera el umbral histórico
CREATE TABLE IF NOT EXISTS alertas_territoriales (
    id                  BIGSERIAL    PRIMARY KEY,
    codigo_dane         VARCHAR(5)   REFERENCES dim_municipios(codigo_dane),
    semana_epi          SMALLINT     NOT NULL,
    anio                SMALLINT     NOT NULL,
    fecha_generacion    TIMESTAMPTZ  DEFAULT NOW(),
    -- 'ALERTA_VERDE' | 'ALERTA_NARANJA' | 'ALERTA_ROJA'
    -- Verde: desviación < 15% sobre media histórica
    -- Naranja: desviación 15-30%
    -- Roja: desviación > 30%
    nivel_alerta        VARCHAR(20) CHECK (nivel_alerta IN ('ALERTA_VERDE', 'ALERTA_NARANJA', 'ALERTA_ROJA')),
    prediccion_casos    NUMERIC(8,2),
    media_historica     NUMERIC(8,2),
    -- % de desviación que activó la alerta — justifica el umbral del 30% (HU15)
    desviacion_pct      NUMERIC(6,2),
    -- Feature más importante según Feature Importance de XGBoost (HU13)
    variable_causal     VARCHAR(50),
    activa              BOOLEAN      DEFAULT TRUE
);





-- ============================================================
-- COMENTARIOS DE DOCUMENTACIÓN
-- (visibles con \d+ en psql — útil para la defensa HU23)
-- ============================================================
COMMENT ON TABLE dim_municipios IS
    'Catálogo de municipios del Valle de Aburrá y Antioquia con geometría PostGIS.
     Fuente: DANE CNPV 2018 + IGAC. Poblar antes que cualquier tabla de hechos.';

COMMENT ON TABLE dim_estaciones_aire IS
    'Catálogo de estaciones de monitoreo. Fuentes: SIATA (radicado 021682) e IDEAM
     (dataset 57sv-p2fu). Permite el cruce estación → municipio del ETL (HU7).';

COMMENT ON TABLE fact_calidad_aire IS
    'Mediciones ambientales por estación y timestamp. Granularidad horaria/diaria.
     Fuente primaria: SIATA. Fuente secundaria: IDEAM datos.gov.co (g4t8-zkc3, kekd-7v7h).';

COMMENT ON TABLE fact_eventos_ira IS
    'Casos individuales de IRA notificados al SIVIGILA. CIE-10 rango J00-J22, J44, J45.
     Fuente: INS. Granularidad: caso por paciente. El GROUP BY se hace en el ETL (HU7).';

COMMENT ON TABLE fact_riesgo_territorial IS
    'Feature Store: tabla analítica maestra resultado del ETL (HU7+HU8).
     Granularidad: 1 fila por municipio por semana epidemiológica.
     Llave de cruce: (codigo_dane, anio, semana_epi).';

COMMENT ON TABLE alertas_territoriales IS
    'Alertas preventivas generadas por el motor XGBoost (HU15).
     Tres niveles: VERDE (<15%), NARANJA (15-30%), ROJA (>30%) sobre media histórica.';

-- ============================================================
-- HECHOS
-- ============================================================


-- -- ============================================================
-- -- COMENTARIOS
-- -- ============================================================
-- COMMENT ON TABLE dim_municipios IS
--     'Municipios del Valle de Aburrá y Antioquia. Fuentes: DANE DIVIPOLA + IGAC (geometría) + ECV Antioquia 2023 (indicadores socioeconómicos). Poblar antes que cualquier tabla de hechos.';

-- COMMENT ON TABLE dim_poblacion_anual IS
--     'Proyecciones de población por municipio y año. Fuente: DANE base CNPV 2018. Necesaria para calcular tasa_ira_100k con el denominador correcto por año histórico.';

-- COMMENT ON TABLE dim_estaciones_aire IS
--     'Catálogo de estaciones de monitoreo. Fuentes: SIATA (radicado 021682) e IDEAM (57sv-p2fu). Permite el cruce estación → municipio en el ETL (HU7).';

-- COMMENT ON TABLE fact_calidad_aire IS
--     'Mediciones ambientales por estación. Fuentes: SIATA + 4 datasets IDEAM (temperatura sbwg-7ju4, precipitación s54a-sgyg, presión 62tk-nxj5, humedad uext-mhny, PM2.5/PM10 g4t8-zkc3).';

-- COMMENT ON TABLE fact_eventos_ira IS
--     'Casos individuales IRA del SIVIGILA 2018-2023 (6 datasets anuales INS). Complementado con Metrosalud (pypc-7h3w) y Eventos SP Envigado (2fzn-ck9b). GROUP BY en ETL (HU7).';

-- COMMENT ON TABLE fact_riesgo_territorial IS
--     'Feature Store: 1 fila por municipio × semana epidemiológica. Resultado del ETL (HU7+HU8). Llave: (codigo_dane, anio, semana_epi).';

-- COMMENT ON TABLE alertas_territoriales IS
--     'Alertas XGBoost (HU15). VERDE <15% / NARANJA 15-30% / ROJA >30% sobre media histórica.';