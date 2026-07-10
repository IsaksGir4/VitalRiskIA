# Diccionario de Datos — VitalRisk AI

## Tabla: fact_riesgo_territorial
Tabla central del sistema. Una fila por municipio × semana epidemiológica.

| Variable | Tipo | Rango | Fuente | Descripción |
|----------|------|-------|--------|-------------|
| codigo_dane | VARCHAR(5) | 05001-05895 | DANE DIVIPOLA | Código único del municipio |
| anio | INTEGER | 2018-2026 | Calculado | Año epidemiológico |
| semana_epi | INTEGER | 1-52 | Calendario INS | Semana epidemiológica |
| fecha_semana | DATE | 2018-01-01 a 2026-07-07 | Calculado | Lunes de la semana epidemiológica |
| casos_ira_total | INTEGER | 0-15 | SIVIGILA/INS | Casos IRA (J00-J22 CIE-10) notificados |
| tasa_ira_100k | NUMERIC | 0-12.5 | Calculado | Tasa de incidencia por 100,000 hab. |
| pm25_avg | NUMERIC | 5-45 µg/m³ | IDEAM SISAIRE | Concentración promedio semanal PM2.5 |
| pm10_avg | NUMERIC | 10-80 µg/m³ | IDEAM SISAIRE | Concentración promedio semanal PM10 |
| temperatura_avg | NUMERIC | 10-32 °C | IDEAM DHIME | Temperatura ambiente promedio |
| humedad_avg | NUMERIC | 50-98 % | IDEAM DHIME | Humedad relativa promedio |
| precipitacion_sum | NUMERIC | 0-500 mm | IDEAM DHIME | Precipitación acumulada semanal |
| presion_avg | NUMERIC | 650-1020 hPa | IDEAM DHIME | Presión atmosférica promedio |
| pm25_lag1 | NUMERIC | 5-45 µg/m³ | Calculado | PM2.5 de la semana anterior |
| casos_ira_lag1 | INTEGER | 0-15 | Calculado | Casos IRA de la semana anterior |
| icv_score | NUMERIC | 0-100 | DANE ECV 2023 | Índice de Condiciones de Vida |
| ipm_pct | NUMERIC | 0-100 % | DANE ECV 2023 | Índice de Pobreza Multidimensional |
| icv_hacinamiento | NUMERIC | 0-100 | DANE ECV 2023 | Componente hacinamiento del ICV |
| icv_seg_social | NUMERIC | 0-15 | DANE ECV 2023 | Componente seguridad social del ICV |
| periodo_pandemia | BOOLEAN | T/F | Calculado | TRUE: 2020-03 a 2021-12 (COVID-19) |
| ipt_score | NUMERIC | 0-100 | Calculado | Índice Preventivo Territorial |
| nivel_riesgo | VARCHAR | BAJO/MEDIO/ALTO | Calculado | Clasificación del IPT |

## Tabla: alertas_territoriales
Alertas generadas por el modelo XGBoost para cada municipio × semana.

| Variable | Tipo | Rango | Descripción |
|----------|------|-------|-------------|
| codigo_dane | VARCHAR(5) | 05001-05895 | Municipio |
| anio | INTEGER | 2018-2026 | Año |
| semana_epi | INTEGER | 1-52 | Semana epidemiológica |
| nivel_alerta | VARCHAR | VERDE/NARANJA/ROJA | VERDE <30%, NARANJA 30-60%, ROJA >60% |
| prediccion_casos | NUMERIC | 0-15 | Predicción XGBoost de casos IRA semana t+1 |
| media_historica | NUMERIC | 0-10 | Media de casos IRA del municipio para esa semana (2018-2023, sin pandemia) |
| desviacion_pct | NUMERIC | -100 a +200 % | Desviación porcentual de la predicción vs media |
| variable_causal | VARCHAR | Nombre de feature | Feature con mayor SHAP value absoluto |
| activa | BOOLEAN | T/F | TRUE si es la alerta más reciente |

## Tabla: dim_municipios
Dimensión estática con datos socioeconómicos y geometría de cada municipio.

| Variable | Tipo | Fuente | Descripción |
|----------|------|--------|-------------|
| codigo_dane | VARCHAR(5) | DANE DIVIPOLA | Clave primaria |
| nombre | VARCHAR | DANE | Nombre del municipio |
| departamento | VARCHAR | DANE | Siempre "Antioquia" |
| subregion | VARCHAR | Gobernación | Subregión (Valle de Aburrá, Urabá, etc.) |
| geometria | GEOMETRY | DANE MGN 2025 | Polígono del municipio (PostGIS) |
| icv_score, nbi, ipm_pct, ... | NUMERIC | DANE ECV 2023 | Variables socioeconómicas |

## Tabla: dim_poblacion_anual
Proyecciones de población DANE para cada municipio por año.

| Variable | Tipo | Rango | Descripción |
|----------|------|-------|-------------|
| codigo_dane | VARCHAR(5) | 05001-05895 | Municipio |
| anio | INTEGER | 2018-2042 | Año de la proyección |
| poblacion_total | INTEGER | 1,000-2,600,000 | Población proyectada |

## Notas Metodológicas

1. **Período pandemia:** Marcado con `periodo_pandemia=TRUE` (2020-03 a 2021-12). No fue excluido del entrenamiento — se usó como variable de control, permitiéndole al modelo aprender la perturbación COVID-19.

2. **PM2.5 2018-2019:** Imputado desde Promedio Anual IDEAM cuando no había datos horarios. Marcado como `fuente_pm='IMPUTADO_PA'`.

3. **IPT:** Métrica compuesta que combina salud (tasa IRA), ambiente (PM2.5) y pobreza (IPM + hacinamiento). No es el mismo concepto que el nivel de alerta del modelo.
