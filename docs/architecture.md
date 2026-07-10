# Arquitectura del Sistema — VitalRisk AI

## Visión General

VitalRisk AI sigue una arquitectura de **tres capas desacopladas** con comunicación via REST:

```
┌──────────────────────────────────────────────────────────┐
│                    CAPA DE DATOS                          │
│  PostgreSQL + PostGIS                                     │
│  7 tablas: 2 dimensiones + 4 hechos + 1 alertas          │
│  Modelo estrella: dim_municipios ↔ fact_riesgo_territorial│
└──────────────────────┬───────────────────────────────────┘
                       │ SQLAlchemy ORM
                       ▼
┌──────────────────────────────────────────────────────────┐
│                    CAPA DE LÓGICA                         │
│  FastAPI + XGBoost + ETL                                  │
│  11 endpoints REST │ SHAP explicabilidad                  │
│  Pipeline ETL: 5 APIs Socrata → Transform → Predict      │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP/JSON
                       ▼
┌──────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                   │
│  Streamlit + Folium                                       │
│  5 vistas │ Mapa coroplético │ KPIs │ Descargas CSV      │
└──────────────────────────────────────────────────────────┘
```

## Decisiones de Arquitectura (ADRs)

### ADR-001: Stack Tecnológico
- **FastAPI sobre Flask:** Validación automática con Pydantic, documentación OpenAPI/Swagger generada, soporte ASGI asíncrono
- **PostgreSQL+PostGIS sobre MongoDB:** JOINs espaciales nativos (`ST_AsGeoJSON`, `ST_Simplify`), SQL estándar para queries analíticas complejas
- **XGBoost sobre SARIMAX:** 103 series temporales simultáneas con 34 features multivariadas. SARIMAX es univariado y no captura interacciones PM2.5 × hacinamiento
- **Docker Compose:** Reproducibilidad garantizada. Un solo `docker-compose up` levanta toda la infraestructura

### ADR-002: Metodología CRISP-ML(Q)
Documentado en detalle. Split cronológico obligatorio por autocorrelación temporal (lag1 r=0.852).

### ADR-003: Diseño del IPT
Fórmula ponderada por percentiles: `0.40×tasa_ira + 0.30×pm25 + 0.15×ipm + 0.15×hacinamiento`. Complementario a las alertas del modelo.

## Pipeline ETL Near-Real-Time

```
┌─────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐
│ EXTRACT │ →  │ TRANSFORM │ →  │ PREDICT  │ →  │  STORE   │
│ 5 APIs  │    │ Semanal   │    │ XGBoost  │    │ UPSERT   │
│ Socrata │    │ por mun.  │    │ + SHAP   │    │ PostGIS  │
└─────────┘    └───────────┘    └──────────┘    └──────────┘
 ~134,000       38 municipios    38 predicciones  fact_riesgo +
 registros      × 1 semana       + alertas        alertas_terr.
```

## Esquema de Base de Datos

```
dim_municipios (125)         dim_poblacion_anual (3,125)
  ├─ codigo_dane (PK)          ├─ codigo_dane (FK)
  ├─ nombre                    ├─ anio
  ├─ geometria (PostGIS)       └─ poblacion_total
  ├─ icv_score, nbi, ipm...
  └─ subregion
        │
        ├──────────────────┐
        ▼                  ▼
fact_riesgo_territorial   alertas_territoriales
  ├─ codigo_dane (FK)       ├─ codigo_dane (FK)
  ├─ anio, semana_epi       ├─ anio, semana_epi
  ├─ casos_ira_total        ├─ nivel_alerta
  ├─ pm25_avg, temp...      ├─ prediccion_casos
  ├─ ipt_score              ├─ variable_causal
  └─ nivel_riesgo           └─ desviacion_pct
```

## Seguridad y Consideraciones Éticas

- **Datos anonimizados:** No se manejan datos individuales de pacientes. Toda la información es agregada a nivel municipal por semana
- **Sin PII:** No hay nombres, cédulas ni historias clínicas en el sistema
- **Datos abiertos:** Todas las fuentes son de dominio público bajo la política de datos abiertos de Colombia
- **Transparencia algorítmica:** SHAP explica cada predicción individual. El usuario puede ver qué variable causó cada alerta
