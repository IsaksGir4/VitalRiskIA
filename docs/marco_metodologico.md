# Marco Metodológico — VitalRisk AI

## Metodología: ASUM-ML

El proyecto siguió **ASUM-ML** (Analytics Solutions Unified Method for Machine Learning), un marco que extiende CRISP-DM integrando prácticas de desarrollo de software ágil (Scrum) y despliegue continuo. Fue adoptado en el Sprint 2 (ADR-002) como evolución de la metodología original.

### Fases ejecutadas

| Fase | Descripción | Artefactos VitalRisk AI |
|---|---|---|
| **Analyze** | Comprensión del negocio y exploración de datos | NB01, NB02, NB03 — EDA de 3 fuentes |
| **Design** | Diseño del Feature Store y decisiones de integración | NB04, NB05 — merge + correlaciones |
| **Configure** | Construcción y ajuste del modelo | NB06, NB07 — IPT + XGBoost |
| **Build** | Motor de alertas y API | NB08, backend/ |
| **Deploy** | Despliegue en producción | Render + Supabase |
| **Operate** | Operación y actualización continua | ETL near-real-time semanal |

## Tipo de Problema

**Regresión supervisada con componente temporal.** Se predice `casos_ira_total` (entero ≥ 0) para la semana t+1 de cada municipio, usando datos históricos hasta la semana t.

## Diseño del Experimento

### Split temporal (sin data leakage)

El dataset histórico (2018-2023, 910 filas) se dividió cronológicamente:

```
Train:      2018-2020  (551 filas — incluye pandemia con flag periodo_pandemia)
Validación: 2021       (103 filas — 100% pandemia, R² negativo esperado)
Test:       2022-2023  (256 filas — métricas operativas reales)
```

El split cronológico es obligatorio en series temporales para evitar que información futura "filtre" hacia el entrenamiento. Un split aleatorio (train/test random) en datos epidemiológicos semanales produciría métricas artificialmente optimistas.

### Construcción de la variable objetivo (target t+1)

```python
df['target_t1'] = df.groupby('codigo_dane')['casos_ira_total'].shift(-1)
```

El modelo predice los casos de la **semana siguiente** usando las features de la **semana actual**. Esto garantiza que en producción, el ETL de esta semana genera predicciones para la semana próxima.

### Features rezagadas (anti-leakage verificado)

```python
df['pm25_lag1'] = df.groupby('codigo_dane')['pm25_avg'].shift(1)
df['casos_ira_lag1'] = df.groupby('codigo_dane')['casos_ira_total'].shift(1)
```

La correlación `pm25_lag1` vs `pm25_avg` = 0.552 (< 1.0) confirma que no hay data leakage: los valores rezagados son diferentes de los actuales.

## Selección de Features

Se aplicaron 6 métodos de selección de features en NB07 y se seleccionaron las 12 features que aparecen en la mayoría de métodos:

| # | Feature | Tipo | Fuente |
|---|---|---|---|
| 1 | `media_hist_mun_sem` | Derivada | Calculada en NB07 (sin leakage) |
| 2 | `casos_ira_total` | Temporal | SIVIGILA |
| 3 | `casos_ira_lag1` | Rezagada | Calculada |
| 4 | `humedad_avg` | Ambiental | IDEAM DHIME |
| 5 | `desviacion_vs_historico` | Derivada | Calculada |
| 6 | `pm25_lag1` | Rezagada | IDEAM SISAIRE |
| 7 | `pm25_avg` | Ambiental | IDEAM SISAIRE |
| 8 | `icv_seg_social` | Socioeconómica | ECV 2023 |
| 9 | `icv_score` | Socioeconómica | ECV 2023 |
| 10 | `ipm_pct` | Socioeconómica | ECV 2023 |
| 11 | `semana_sin` | Estacionalidad | Calculada (seno de semana/52) |
| 12 | `semana_cos` | Estacionalidad | Calculada (coseno de semana/52) |

## Algoritmo Seleccionado: XGBoost

Se compararon 7 algoritmos en el conjunto de validación. XGBoost fue seleccionado por:

- Mejor RMSE en validación entre todos los modelos evaluados
- Manejo nativo de valores nulos (`tree_method='hist'`), necesario dado el 30-36% de NaN en variables ambientales
- Velocidad de inferencia adecuada para el ETL near-real-time (103 predicciones en <1 segundo)
- Explicabilidad mediante SHAP TreeExplainer (requerimiento del concurso)

Justificación detallada vs SARIMAX en ADR-003, sección 4.

## Índice Preventivo Territorial (IPT)

El IPT es una métrica compuesta que captura la vulnerabilidad estructural del municipio, independiente de la predicción del modelo:

```
IPT = 0.40 × percentil(tasa_ira_100k)
    + 0.30 × percentil(pm25_avg)
    + 0.15 × percentil(ipm_pct)
    + 0.15 × percentil(icv_hacinamiento)
```

Los percentiles se calculan dentro de la distribución de todos los municipios de Antioquia para la misma semana. Escala 0-100: BAJO (0-33) / MEDIO (34-66) / ALTO (67-100).

## Motor de Alertas

Las alertas comparan la predicción XGBoost del municipio con su media histórica para esa semana del año (calculada con datos 2018-2023, excluyendo pandemia):

```
desviacion = (prediccion - media_historica) / media_historica × 100

ALERTA_VERDE:   desviacion < 30%   (≤ P92 histórico)
ALERTA_NARANJA: 30% ≤ desviacion < 60%
ALERTA_ROJA:    desviacion ≥ 60%   (> P95 histórico)
```

Los umbrales se calibraron con el análisis de percentiles del histórico en NB05 (HU9), documentado en ADR-003 sección 3.5.

## Explicabilidad (SHAP)

Para cada predicción individual, el sistema usa SHAP TreeExplainer para identificar la `variable_causal`: la feature con mayor valor SHAP absoluto. Esta variable se almacena en `alertas_territoriales.variable_causal` y se muestra en el dashboard. La variable causal más frecuente globalmente es `pm25_avg` (25.4% de los registros).

## Validación Cruzada Temporal

Se aplicó `TimeSeriesSplit` con 5 folds sobre el conjunto train+validación para estimar la varianza del modelo:

| Métrica | Media CV | Std CV |
|---|---|---|
| RMSE | ~1.74 | 1.48 |
| R² | variable | alta (por pandemia en algunos folds) |

La alta varianza en CV es esperada: el fold que incluye 2020-2021 tiene R² negativo por la pandemia, mientras que los folds sin pandemia muestran R² > 0.6.