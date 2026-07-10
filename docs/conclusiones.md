# Conclusiones, Limitaciones y Próximos Pasos

## Hallazgos Principales

1. **La autocorrelación temporal es la señal más fuerte para predecir IRA.** Las features `casos_ira_lag1` (0.388 gain) y `casos_ira_total` (0.360 gain) dominan la importancia del modelo. Los brotes respiratorios tienen inercia temporal — si hay muchos casos esta semana, probablemente habrá muchos la siguiente.

2. **PM2.5 es la variable ambiental más relevante.** Es la variable causal más frecuente en las alertas (25.4%), validando la hipótesis de que la calidad del aire es un predictor significativo de brotes respiratorios. Esto tiene implicaciones de política pública: mejorar la calidad del aire tiene un impacto medible en la carga de enfermedad respiratoria.

3. **Las variables socioeconómicas aportan contexto pero no predicción directa.** `icv_seg_social` es la 3ra feature por importancia (0.048 gain), pero su contribución es menor comparada con las señales temporales y ambientales. Sin embargo, son fundamentales para el IPT, que mide vulnerabilidad estructural.

4. **El período pandemia (2020-2021) es un perturbador aprendible.** En vez de excluirlo, lo usamos como variable de control (`periodo_pandemia=TRUE`). El modelo aprendió que los casos colapsaron durante cuarentenas. Esto es una fortaleza metodológica, no una limitación.

5. **38 de 103 municipios tienen estaciones meteorológicas activas.** La cobertura de estaciones IDEAM en Antioquia es parcial. El modelo usa `fill_values` (medianas históricas) para los municipios sin estación. Ampliar la red de estaciones mejoraría las predicciones.

## Limitaciones Honestas

1. **SIVIGILA no tiene API pública con datos 2025-2026.** El sistema usa la media histórica como proxy de casos IRA actuales. Cuando existan datos SIVIGILA recientes, las alertas reflejarán desviaciones reales en vez de ~0%.

2. **PM2.5 de SISAIRE tiene rezago de ~6 meses.** El último dato disponible es de diciembre 2024. El pipeline incorporará datos más recientes automáticamente cuando SISAIRE publique actualizaciones.

3. **R² negativo en validación (2021).** El validation set es 100% período pandemia. R²=0.607 en test (2022-2023) es la métrica relevante para producción. La varianza de la CV temporal (σ=1.48) es esperada por la heterogeneidad temporal.

4. **Solo se monitorea IRA.** SaluData de Bogotá monitorea 15+ eventos trazadores. Ampliar a dengue, malaria y otros eventos es viable con la misma arquitectura.

5. **Una sola validación de alerta.** Se compara predicción vs media histórica. SaluData usa tres validaciones (vs año anterior, vs mes anterior, vs predicción). Implementar validación triple mejoraría la especificidad de las alertas.

## Próximos Pasos

### Corto plazo (post-concurso)
- Integrar SIVIGILA 2024-2025 cuando esté disponible
- Agregar SIATA como fuente directa de PM2.5 (radicado 021682 pendiente)
- Implementar notificaciones automatizadas (correo, Telegram)
- Ampliar a otros eventos trazadores (dengue, malaria)

### Mediano plazo
- Reentrenamiento automático del modelo cada trimestre
- Dashboard comparativo multi-departamental
- API pública para consumo de terceros
- Integración con MIPRES para correlación con medicamentos respiratorios

### Largo plazo
- Modelo ensemble (XGBoost + LSTM para componente temporal)
- Detección de anomalías no supervisada
- Sistema multiagente con LLM para generación de reportes automáticos
- Escalamiento a nivel nacional (32 departamentos)
