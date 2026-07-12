# Arquitectura del Sistema — VitalRisk AI

## Visión General

VitalRisk AI sigue una arquitectura de **tres capas desacopladas** desplegadas en servicios cloud, con comunicación vía REST:

```mermaid
flowchart TB
    subgraph Presentacion ["Capa de Presentación — Render Web Service"]
        UI["Streamlit App\n5 Vistas + Folium\nvitalriskia-frontend.onrender.com"]
    end

    subgraph Logica ["Capa de Lógica — Render Web Service"]
        API["FastAPI\n11 Endpoints REST\nvitalriskia.onrender.com"]
        ML["XGBoost .pkl + SHAP TreeExplainer\n12 features · RMSE=1.74"]
        ETL_Job["Pipeline ETL Near-Real-Time\n5 APIs Socrata → 38 municipios"]

        API <--> ML
        API --> ETL_Job
    end

    subgraph Datos ["Capa de Datos — Supabase (PostgreSQL gestionado)"]
        DB[("PostgreSQL + PostGIS\n7 tablas · 948+ filas fact_riesgo")]
        Schema["dim_municipios (125)\ndim_poblacion_anual (3,125)\nfact_calidad_aire (12,354)\nfact_eventos_ira (910)\nfact_riesgo_territorial (948+)\nalerts_territoriales (845+)"]
        DB --- Schema
    end

    UI == "HTTPS/JSON\nAPI_URL env var" ==> API
    API == "SQLAlchemy Session Pooler :5432" ==> DB
    ETL_Job == "Upsert espacial ON CONFLICT" ==> DB
```

## Decisiones de Arquitectura (ADRs)

| Decisión | Elegido | Descartado | Razón |
|---|---|---|---|
| Backend | FastAPI | Flask | Validación Pydantic, ASGI asíncrono, OpenAPI automático |
| Base de datos | PostgreSQL+PostGIS (Supabase) | MongoDB | JOINs espaciales nativos, SQL estándar para queries analíticas |
| Modelo | XGBoost | SARIMAX, Random Forest, Ridge | 103 series simultáneas, 12 features multivariadas, nulos nativos |
| Orquestación | Docker Compose (local) + Render PaaS (prod) | Kubernetes | MVP en 3 meses con 2 personas |
| Frontend | Streamlit | React | Velocidad de desarrollo, componentes geoespaciales nativos |

Ver ADR-001, ADR-002, ADR-003 para justificaciones detalladas.

## Topología de Conexiones en Producción

```
Local (desarrollo):
  ETL / load_to_db.py  ──→  Supabase :5432 (Direct Connection)
  uvicorn backend      ──→  Supabase :5432 (Session Pooler)

Producción (Render):
  Frontend Streamlit   ──→  API_URL=https://vitalriskia.onrender.com
  FastAPI backend      ──→  Supabase :5432 (Session Pooler via env vars Render)
```

**Nota sobre Session Pooler:** FastAPI usa PgBouncer vía Supabase Session Pooler (puerto 6543) para conexiones de baja latencia. El ETL de carga inicial usa Direct Connection (puerto 5432) para transacciones pesadas sin restricciones de prepared statements.

## Pipeline ETL Near-Real-Time

```mermaid
graph LR
    A["EXTRACT\n5 APIs Socrata\n~134,000 registros"] --> B["TRANSFORM\nAgregación semanal\npor municipio"]
    B --> C["PREDICT\nXGBoost\n38 predicciones"]
    C --> D["STORE\nUPSERT PostGIS\nfact_riesgo +\nalertas_territoriales"]
```

Activación: `POST /api/v1/etl/sincronizar?dias_atras=14`

## Esquema de Base de Datos (init.sql v4)

```mermaid
erDiagram
    dim_municipios {
        varchar5 codigo_dane PK
        varchar nombre
        varchar departamento
        varchar subregion
        integer poblacion_2023
        numeric icv_score
        numeric icv_hacinamiento
        numeric icv_menores_6
        numeric icv_seg_social
        numeric icv_paredes
        numeric icv_pisos
        numeric pct_vivienda_acueducto
        numeric nbi
        numeric ipm_pct
        geometry geometria
    }

    dim_poblacion_anual {
        varchar5 codigo_dane FK
        smallint anio
        integer poblacion_total
    }

    dim_estaciones_aire {
        varchar30 estacion_id PK
        varchar nombre
        varchar20 fuente
        varchar5 codigo_dane FK
        numeric latitud
        numeric longitud
        geometry ubicacion
    }

    fact_calidad_aire {
        bigserial id PK
        varchar5 codigo_dane FK
        smallint anio
        smallint semana_epi
        numeric pm25_avg
        numeric pm10_avg
        numeric temperatura_avg
        numeric humedad_avg
        numeric precipitacion_sum
        numeric presion_avg
        varchar20 fuente_pm
    }

    fact_eventos_ira {
        bigserial id PK
        varchar5 codigo_dane FK
        smallint semana_epi
        smallint anio
        date fecha_semana
        integer casos_ira_total
        numeric edad_promedio
        numeric rezago_reporte_dias
        numeric pct_regimen_contributivo
        boolean periodo_pandemia
        varchar20 fuente_dato
    }

    fact_riesgo_territorial {
        bigserial id PK
        varchar5 codigo_dane FK
        smallint semana_epi
        smallint anio
        integer casos_ira_total
        numeric tasa_ira_100k
        numeric pm25_avg
        numeric pm25_lag1
        numeric casos_ira_lag1
        numeric icv_score
        numeric ipm_pct
        numeric icv_hacinamiento
        numeric ipt_score
        varchar10 nivel_riesgo
        boolean periodo_pandemia
    }

    alertas_territoriales {
        bigserial id PK
        varchar5 codigo_dane FK
        smallint semana_epi
        smallint anio
        varchar20 nivel_alerta
        numeric prediccion_casos
        numeric media_historica
        numeric desviacion_pct
        varchar50 variable_causal
        boolean activa
    }

    dim_municipios ||--o{ dim_poblacion_anual : "codigo_dane"
    dim_municipios ||--o{ dim_estaciones_aire : "codigo_dane"
    dim_municipios ||--o{ fact_calidad_aire : "codigo_dane"
    dim_municipios ||--o{ fact_eventos_ira : "codigo_dane"
    dim_municipios ||--o{ fact_riesgo_territorial : "codigo_dane"
    dim_municipios ||--o{ alertas_territoriales : "codigo_dane"
```

**Nota:** `dim_estaciones_aire` está reservada para datos SIATA (radicado 021682, pendiente). Actualmente vacía — los datos ambientales se agregaron a nivel municipio-semana en el NB02 mediante spatial join.

## Seguridad y Ética

- **Datos anonimizados:** no hay datos individuales de pacientes. Todo está agregado a nivel municipal por semana epidemiológica.
- **Sin PII:** sin nombres, cédulas ni historias clínicas.
- **Datos abiertos:** todas las fuentes son de dominio público bajo la política de datos abiertos de Colombia.
- **Transparencia algorítmica:** SHAP explica cada predicción. El usuario puede ver qué variable causó cada alerta.
- **Limitación documentada:** SIVIGILA no tiene API pública con datos 2025-2026. El modelo usa media histórica como proxy. Las alertas reflejarán desviaciones reales cuando existan datos SIVIGILA recientes.