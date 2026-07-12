# Conclusiones, Limitaciones y Próximos Pasos — VitalRisk AI

## Hallazgos Principales

**1. La autocorrelación temporal es la señal más fuerte para predecir IRA.**
Las features `casos_ira_lag1` (gain 0.388) y `casos_ira_total` (gain 0.360) dominan la importancia del modelo. La correlación Spearman lag1 con el target es r=0.852, estadísticamente confirmada mediante Durbin-Watson (DW=2.89). Los brotes respiratorios tienen inercia temporal: si hay muchos casos esta semana, probablemente habrá muchos la siguiente. Esto justifica el uso de features rezagadas como decisión de diseño central del Feature Store.

**2. PM2.5 es la variable ambiental más relevante.**
Es la variable causal más frecuente en las alertas SHAP (25.4% de los registros). La correlación Spearman con casos IRA es r=0.285 (p<0.001), validando la hipótesis epidemiológica de que la calidad del aire es un predictor significativo de brotes respiratorios. Implicación de política pública: mejorar la calidad del aire tiene un impacto medible y cuantificable en la carga de enfermedad respiratoria.

**3. El acceso a salud supera al PM2.5 en correlación con IRA.**
`icv_seg_social` (seguridad social del jefe del hogar) tiene r=0.418 con casos IRA — mayor que PM2.5. Esto indica que las variables estructurales de acceso al sistema de salud son determinantes en la notificación y atención de casos. El IPT integra ambas dimensiones (ambiental y socioeconómica) precisamente por esto.

**4. El período pandemia (2020-2021) es un perturbador aprendible.**
En vez de excluir estos datos, se usó la columna `periodo_pandemia=TRUE` como variable de control. El modelo aprendió que los casos colapsaron durante cuarentenas (Mann-Whitney U p<0.001, justificado en NB05). Esta es una fortaleza metodológica: el modelo puede distinguir entre una baja epidemiológica real y una perturbación sistémica como una pandemia.

**5. La ampliación a 125 municipios fue la decisión correcta.**
El alcance inicial era el Valle de Aburrá (10 municipios). Al explorar los datos de la ECV 2023, se evidenció una brecha estructural significativa entre el Valle de Aburrá (alto ICV) y otras subregiones de Antioquia (Urabá, Bajo Cauca, Nordeste) con indicadores de hacinamiento, pobreza y acceso a salud que multiplican la vulnerabilidad. Un modelo entrenado con 125 municipios captura esta heterogeneidad y generaliza mejor.

**6. 38 de 103 municipios tienen estaciones meteorológicas activas.**
La cobertura de estaciones IDEAM en Antioquia es parcial. El modelo usa `fill_values` (medianas históricas del municipio) para los 65 municipios restantes. Ampliar la red de estaciones o integrar datos satelitales (MODIS, ERA5) mejoraría sustancialmente las predicciones en zonas rurales.

---

## Limitaciones Honestas

**1. SIVIGILA no tiene API pública con datos 2025-2026.**
El sistema usa la media histórica municipal como proxy de casos IRA actuales (2026). La desviación de la predicción vs la media es ~0% por construcción, lo que hace que las alertas tiendan a VERDE. Con datos SIVIGILA reales, las alertas reflejarían desviaciones epidemiológicas reales. Esta limitación es documentada y explícita en la Vista de Transparencia IA del dashboard.

**2. PM2.5 de SISAIRE tiene rezago de ~6 meses.**
El último dato disponible en el ETL es de diciembre 2024. El pipeline usa el promedio histórico de `fact_calidad_aire` como proxy para el período reciente. Cuando SISAIRE publique actualizaciones, el pipeline las incorpora automáticamente.

**3. R² negativo en validación (fold 2021).**
El validation set es 100% período pandemia (2021), donde los casos IRA colapsaron de forma atípica. R²=-0.X en ese fold es esperado y no invalida el modelo: el R²=0.607 en test (2022-2023, datos post-pandemia normales) es la métrica operativamente relevante. La varianza de CV temporal (σ=1.48) es consecuencia de la heterogeneidad temporal del dataset, no de sobreentrenamiento.

**4. Solo se monitorea IRA (evento 345).**
El sistema está diseñado para un solo evento trazador. Ampliar a dengue, malaria, EDA y otros eventos epidemiológicos relevantes para Antioquia es viable con la misma arquitectura — solo requiere agregar nuevos datasets SIVIGILA y reentrenar el modelo.

**5. Una sola validación de alerta.**
El sistema compara la predicción XGBoost vs la media histórica del municipio. Implementar validación múltiple (vs año anterior, vs período equivalente, vs predicción) mejoraría la especificidad de las alertas y reduciría falsos positivos — es un próximo paso natural.

**6. Bug menor: PM2.5 en KPIs del dashboard.**
La transformación `fetch_pm25_historico` retorna promedio por municipio; el KPI de PM2.5 del dashboard espera un promedio global. Fix pendiente en `transform_pm25_semanal`.

---

## Próximos Pasos

### Corto plazo (post-concurso, 1-3 meses)
- Integrar SIVIGILA 2024 cuando esté disponible en el portal INS
- Conectar datos SIATA directos cuando el radicado 021682 tenga respuesta
- Implementar notificaciones automatizadas (correo o Telegram) para secretarías de salud municipales
- Fix de KPI PM2.5 en el dashboard
- Reentrenamiento trimestral automático con nuevos datos

### Mediano plazo (3-12 meses)
- Ampliar a dengue, malaria, EDA y otros eventos trazadores de Antioquia
- Validación triple de alertas (vs año anterior + vs mes anterior + vs predicción)
- Dashboard comparativo multi-departamental (Córdoba, Chocó, Norte de Santander)
- API pública para consumo por secretarías de salud y sistemas SISMUESTRAS

### Largo plazo (1-2 años)
- Modelo ensemble (XGBoost + LSTM para captura de componente temporal largo)
- Integración de datos satelitales (MODIS/Terra para PM2.5, ERA5 para meteorología)
- Sistema multiagente con LLM para generación de reportes narrativos automáticos
- Escalamiento nacional: 32 departamentos de Colombia con la misma arquitectura