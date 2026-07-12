# Planteamiento del Problema — VitalRisk AI

## Contexto

Las Infecciones Respiratorias Agudas (IRA) son la principal causa de consulta de urgencias en Antioquia. Según el SIVIGILA/INS, el departamento registra miles de casos semanales, con picos estacionales en los períodos de lluvia (semanas 10-15 y 35-45 del año epidemiológico) y una distribución territorial marcadamente desigual: los municipios del Valle de Aburrá concentran la mayoría de los casos notificados, pero los municipios rurales del Bajo Cauca, Urabá y Nordeste presentan tasas de incidencia más altas por 100,000 habitantes, agravadas por menor acceso al sistema de salud y condiciones de hacinamiento y pobreza más severas.

## El Problema

**Los sistemas de alerta de salud pública en Colombia son reactivos.** La vigilancia epidemiológica actual (SIVIGILA) reporta casos una vez que ya se han presentado. No existe en Antioquia un sistema público que:

1. **Integre** simultáneamente datos de calidad del aire (PM2.5/PM10), variables meteorológicas, casos epidemiológicos y vulnerabilidad socioeconómica a nivel territorial.
2. **Anticipe** con al menos una semana de antelación dónde y cuándo ocurrirá el próximo pico de IRA en cada municipio.
3. **Explique** qué variable (ambiental, climática o socioeconómica) está causando el riesgo elevado, para orientar intervenciones específicas.

En Colombia existen iniciativas de observatorios de salud pública a nivel de grandes ciudades, pero no existe un sistema equivalente para los 125 municipios de Antioquia que integre calidad del aire, epidemiología y vulnerabilidad socioeconómica en un modelo predictivo multivariado.

## Pregunta de Investigación

> ¿Es posible predecir, con al menos una semana de anticipación y con un error menor al de la media histórica, el número de casos de IRA en cada municipio de Antioquia, integrando variables de calidad del aire, meteorología y vulnerabilidad socioeconómica de fuentes de datos abiertos?

## Hipótesis

La combinación de variables rezagadas de PM2.5 (exposición acumulada), autocorrelación temporal de casos IRA y variables de vulnerabilidad socioeconómica (hacinamiento, pobreza multidimensional) permite construir un modelo multivariado (XGBoost) que supera en más de un 15% el RMSE del baseline naive (media histórica por municipio-semana), y que puede ejecutarse en tiempo real con datos disponibles en APIs de datos abiertos de Colombia.

## Población Objetivo

**Beneficiarios directos:** Secretarías municipales de salud de Antioquia, responsables de la vigilancia epidemiológica y la activación de planes de contingencia respiratoria.

**Beneficiarios indirectos:** Los ~6.8 millones de habitantes de Antioquia, especialmente grupos vulnerables — menores de 5 años, adultos mayores y personas en condición de pobreza multidimensional.

## Alcance del Proyecto

- **Territorial:** 103 municipios de Antioquia con registro epidemiológico activo en SIVIGILA (125 con geometría). Incluye el Valle de Aburrá como zona prioritaria.
- **Temporal:** histórico 2018-2023 para entrenamiento y validación. Datos en tiempo real desde APIs Socrata (IDEAM) para el sistema de alertas.
- **Variable objetivo:** `casos_ira_total` (casos de IRA evento 345 notificados por municipio y semana epidemiológica).
- **Horizonte de predicción:** t+1 (una semana de anticipación).
- **Fuera de alcance:** diagnóstico clínico individual, otros eventos epidemiológicos distintos a IRA, departamentos fuera de Antioquia.

## Justificación del Enfoque de Datos Abiertos

Todas las fuentes utilizadas son de dominio público bajo la Ley 1712 de 2014 (Transparencia y Acceso a la Información Pública):
- **datos.gov.co:** 5 APIs Socrata del IDEAM (PM2.5, temperatura, humedad, precipitación, presión).
- **ins.gov.co:** SIVIGILA — eventos IRA 2018-2023.
- **dane.gov.co / geoportal.dane.gov.co:** geometrías MGN2025 y proyecciones CNPV 2018.
- **antioquiadatos.gov.co:** Encuesta de Calidad de Vida Antioquia 2023.

El sistema es replicable en cualquier departamento de Colombia que cuente con estaciones IDEAM activas y registro SIVIGILA, sin costo adicional de adquisición de datos.