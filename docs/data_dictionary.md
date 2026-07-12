# Diccionario de Datos — VitalRisk AI

## Tabla: fact_riesgo_territorial
Tabla central del sistema (Feature Store). Una fila por municipio × semana epidemiológica.

| Variable | Tipo | Rango | Fuente | Descripción |
|----------|------|-------|--------|-------------|
| codigo_dane | VARCHAR(5) | 05001-05895 | DANE DIVIPOLA | Código único del municipio (siempre 5 dígitos con cero inicial) |
| anio | SMALLINT | 2018-2026 | Calculado | Año epidemiológico |
| semana_epi | SMALLINT | 1-53 | Calendario INS | Semana epidemiológica (lunes ISO) |
| fecha_semana | DATE | 2018-01-01 a 2026-07-07 | Calculado | Lunes de la semana epidemiológica |
| casos_ira_total | INTEGER | 0-15 | SIVIGILA/INS | Casos IRA (evento 345) notificados en esa semana |
| tasa_ira_100k | NUMERIC | 0-12.5 | Calculado | (casos / población_año) × 100,000 |
| pm25_avg | NUMERIC | 5-45 µg/m³ | IDEAM SISAIRE | Concentración promedio semanal PM2.5. Fuente: `fuente_pm` |
| pm10_avg | NUMERIC | 10-80 µg/m³ | IDEAM SISAIRE | Concentración promedio semanal PM10 |
| temperatura_avg | NUMERIC | 10-32 °C | IDEAM DHIME | Temperatura ambiente promedio semanal |
| humedad_avg | NUMERIC | 50-98 % | IDEAM DHIME | Humedad relativa promedio semanal |
| precipitacion_sum | NUMERIC | 0-500 mm | IDEAM DHIME | Precipitación acumulada semanal |
| presion_avg | NUMERIC | 650-1020 hPa | IDEAM DHIME | Presión atmosférica promedio (cobertura ~15% — pocas estaciones) |
| fuente_pm | VARCHAR(20) | SISAIRE_DIRECTO / IMPUTADO_PA / NULL | Calculado | Trazabilidad: directo 2020-2023, imputado desde Promedio Anual 2018-2019 |
| pm25_lag1 | NUMERIC | 5-45 µg/m³ | Calculado | PM2.5 de la semana t-1 (exposición reciente) |
| pm25_lag2 | NUMERIC | 5-45 µg/m³ | Calculado | PM2.5 de la semana t-2 (exposición acumulada) |
| casos_ira_lag1 | INTEGER | 0-15 | Calculado | Casos IRA de la semana t-1 (autocorrelación r=0.852) |
| icv_score | NUMERIC | 0-100 | DANE ECV 2023 | Índice de Condiciones de Vida |
| ipm_pct | NUMERIC | 0-100 % | DANE ECV 2023 | Índice de Pobreza Multidimensional |
| icv_hacinamiento | NUMERIC | 0-100 | DANE ECV 2023 | Componente hacinamiento del ICV |
| icv_seg_social | NUMERIC | 0-15 | DANE ECV 2023 | Seguridad social jefe del hogar (r=0.418 con IRA — mayor feature socioecon.) |
| icv_paredes | NUMERIC | 0-100 | DANE ECV 2023 | D4 V3 — Paredes de material no adecuado |
| icv_pisos | NUMERIC | 0-100 | DANE ECV 2023 | D4 V4 — Pisos de material no adecuado |
| periodo_pandemia | BOOLEAN | TRUE/FALSE | Calculado | TRUE: 2020-03-01 a 2021-12-31 (COVID-19). Justificado: Mann-Whitney p<0.001 |
| ipt_score | NUMERIC | 0-100 | Calculado HU11 | Índice Preventivo Territorial (ver fórmula abajo) |
| nivel_riesgo | VARCHAR(10) | BAJO/MEDIO/ALTO | Calculado HU11 | BAJO (0-33) · MEDIO (34-66) · ALTO (67-100) |

## Tabla: alertas_territoriales
Alertas generadas por el modelo XGBoost para cada municipio × semana.

| Variable | Tipo | Valores posibles | Descripción |
|----------|------|-----------------|-------------|
| codigo_dane | VARCHAR(5) | 05001-05895 | Municipio |
| anio | SMALLINT | 2018-2026 | Año |
| semana_epi | SMALLINT | 1-53 | Semana epidemiológica |
| nivel_alerta | VARCHAR(20) | ALERTA_VERDE · ALERTA_NARANJA · ALERTA_ROJA | Ver umbrales abajo |
| prediccion_casos | NUMERIC | 0-15 | Predicción XGBoost de casos IRA semana t+1 |
| media_historica | NUMERIC | 0-10 | Media de casos IRA del municipio para esa semana del año (2018-2023, excluyendo pandemia) |
| desviacion_pct | NUMERIC | -100 a +200 % | `(prediccion - media_historica) / media_historica × 100` |
| variable_causal | VARCHAR(50) | Nombre de feature | Feature con mayor SHAP value absoluto para esa predicción |
| activa | BOOLEAN | TRUE/FALSE | TRUE si es la alerta más reciente para ese municipio-semana |

### Umbrales de alerta

Los umbrales se calibraron con base en el análisis de percentiles del histórico 2018-2023 (excluyendo pandemia) en NB05:

| Nivel | Condición | Percentil histórico equivalente | Interpretación |
|---|---|---|---|
| **ALERTA_VERDE** | desviación_pct < 30% | ≤ P92 | Comportamiento dentro del rango esperable |
| **ALERTA_NARANJA** | 30% ≤ desviación < 60% | P92-P95 | Brote moderado previsto — vigilancia aumentada |
| **ALERTA_ROJA** | desviación_pct ≥ 60% | > P95 | Brote severo previsto — intervención recomendada |

## Tabla: dim_municipios
Dimensión estática con datos socioeconómicos y geometría de cada municipio.

| Variable | Tipo | Fuente | Descripción |
|----------|------|--------|-------------|
| codigo_dane | VARCHAR(5) | DANE DIVIPOLA | Clave primaria (siempre 5 dígitos: 05001 = Medellín) |
| nombre | VARCHAR | DANE | Nombre oficial del municipio |
| departamento | VARCHAR | DANE | Siempre "Antioquia" en este proyecto |
| subregion | VARCHAR | Gobernación | Ej. "Valle de Aburrá", "Urabá", "Oriente" |
| geometria | GEOMETRY(MultiPolygon,4326) | DANE MGN 2025 | Polígono del municipio en EPSG:4326 |
| icv_score, nbi, ipm_pct, icv_hacinamiento, icv_menores_6, icv_seg_social, pct_vivienda_acueducto, icv_paredes, icv_pisos | NUMERIC | DANE ECV Antioquia 2023 | 9 indicadores socioeconómicos invariantes (Zona=Total) |
| poblacion_2023 | INTEGER | DANE CNPV 2018 | Población proyectada 2023 (referencia rápida sin JOIN) |

## Tabla: dim_poblacion_anual
Proyecciones de población DANE para cada municipio por año.

| Variable | Tipo | Rango | Descripción |
|----------|------|-------|-------------|
| codigo_dane | VARCHAR(5) | 05001-05895 | Municipio |
| anio | SMALLINT | 2018-2042 | Año de la proyección |
| poblacion_total | INTEGER | 1,000-2,600,000 | Población proyectada base CNPV 2018 |

## Índice Preventivo Territorial (IPT)

```
IPT = 0.40 × percentil(tasa_ira_100k)
    + 0.30 × percentil(pm25_avg)
    + 0.15 × percentil(ipm_pct)
    + 0.15 × percentil(icv_hacinamiento)
```

**Escala:** 0-100. **Clasificación:** BAJO (0-33) · MEDIO (34-66) · ALTO (67-100).

El IPT mide **vulnerabilidad estructural** del territorio. Las alertas del modelo miden **desviación de la predicción** vs la media histórica. Son señales complementarias, no redundantes: un municipio puede tener IPT ALTO (vulnerable) con ALERTA_VERDE (sin brote previsto esta semana), o IPT BAJO con ALERTA_ROJA (brote atípico).

## Notas Metodológicas

1. **Período pandemia:** marcado con `periodo_pandemia=TRUE` para 2020-03-01 a 2021-12-31. No excluido — se usa como variable de control. Justificado estadísticamente: Mann-Whitney U p<0.001.

2. **PM2.5 2018-2019:** imputado desde Promedio Anual IDEAM (`fuente_pm='IMPUTADO_PA'`) usando distribución Normal(media_PA, std_estimada). Los datos directos SISAIRE comienzan en 2020.

3. **Cobertura de estaciones:** 38 de 103 municipios tienen estaciones IDEAM activas. Los municipios sin estación reciben valores por vecino espacial más cercano (interpolación documentada en NB02).

4. **`codigo_dane` siempre VARCHAR(5):** el código nunca se trata como entero. Siempre `str.zfill(5)`. Error frecuente: 5001 en vez de '05001'.