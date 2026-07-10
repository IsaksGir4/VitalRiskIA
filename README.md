# VitalRisk AI — Sistema de Vigilancia Preventiva Territorial en Salud

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.1-orange.svg)](https://xgboost.ai)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.3-4CAF50.svg)](https://postgis.net)
[![Licencia MIT](https://img.shields.io/badge/Licencia-MIT-green.svg)](LICENSE)

> **Equipo 326** | Datos al Ecosistema 2026 — IA para Colombia (MinTIC)
> Reto: Salud — Innovación Social

---

## El Problema

Las alertas de salud pública en Colombia son **reactivas**: llegan cuando el brote ya está ocurriendo. No existe un sistema público que integre calidad del aire, epidemiología y datos socioeconómicos para predecir dónde y cuándo ocurrirá el próximo pico de enfermedad respiratoria en Antioquia.

Cada año, las Infecciones Respiratorias Agudas (IRA) generan miles de consultas de urgencias en Antioquia. Los municipios más vulnerables — con alta contaminación por PM2.5, hacinamiento y pobreza — son los más afectados y los que menos capacidad tienen para responder a tiempo.

## La Solución

**VitalRisk AI** predice brotes de IRA con **una semana de anticipación** para los 103 municipios de Antioquia, integrando en tiempo real:

- **Calidad del aire** — PM2.5 y PM10 desde IDEAM SISAIRE (API Socrata)
- **Variables meteorológicas** — Humedad, temperatura, precipitación y presión desde IDEAM DHIME (4 APIs Socrata)
- **Epidemiología** — Casos IRA semanales desde SIVIGILA/INS (2018-2023)
- **Vulnerabilidad socioeconómica** — ECV Antioquia 2023 (DANE)
- **Demografía** — Proyecciones poblacionales DANE 2018-2042

El sistema calcula un **Índice Preventivo Territorial (IPT)** por municipio y genera alertas preventivas explicables mediante **SHAP**, identificando qué variable causó cada alerta.

## Resultados del Modelo

| Métrica | Valor | Interpretación |
|---------|-------|----------------|
| **RMSE** | 1.7399 | Error promedio de 1.74 casos/municipio-semana |
| **MAE** | 1.0295 | Error absoluto medio de ~1 caso |
| **R²** | 0.607 | Explica el 60.7% de la varianza |
| **Mejora vs Naive** | +16.2% | Supera el baseline de media histórica |

Modelo XGBoost entrenado con **split cronológico** (2018-2020 train / 2021 validation / 2022-2023 test) para evitar data leakage temporal. Validación cruzada con TimeSeriesSplit (5 folds).

## Arquitectura

```
  IDEAM Socrata (4 APIs)     SISAIRE Socrata        Metadata DANE
  Humedad · Temp · Precip     PM2.5 (g4t8-zkc3)     ECV · Población
  Presión atmosférica                                Geometrías MGN
          │                        │                       │
          └────────────┬───────────┘───────────────────────┘
                       ▼
              ETL Near-Real-Time
              (5 fuentes Socrata → PostgreSQL)
                       │
                       ▼
          ┌────────────────────────┐
          │  PostgreSQL + PostGIS  │
          │  7 tablas · 948+ filas │
          └────────────┬───────────┘
                       │
                       ▼
          ┌────────────────────────┐
          │  FastAPI Backend       │
          │  11 endpoints REST     │
          │  XGBoost + SHAP        │
          └────────────┬───────────┘
                       │
                       ▼
          ┌────────────────────────┐
          │  Streamlit Frontend    │
          │  Mapa Folium + KPIs   │
          │  5 vistas interactivas│
          └────────────────────────┘
```

## Funcionalidades

### Dashboard Territorial
Mapa coroplético de Antioquia coloreado por IPT (verde/amarillo/rojo) con tooltips por municipio, panel de alertas recientes y 5 KPIs en tiempo real.

### Alertas Preventivas
Tarjetas de alerta con predicción t+1, desviación porcentual vs media histórica y variable causal identificada por SHAP. Predicción en vivo con un clic.

### Transparencia IA
Métricas de rendimiento del modelo, feature importance (XGBoost gain), validación cruzada temporal, explicabilidad SHAP y justificaciones técnicas de decisiones de diseño.

### Portal de Datos Abiertos
Descargas CSV del IPT y alertas, diccionario de datos y metadatos siguiendo el estándar del Observatorio de Salud de Bogotá (SaluData).

### ETL Near-Real-Time
Pipeline que conecta a 5 APIs Socrata de datos.gov.co, extrae ~134,000 registros climáticos, los transforma a granularidad municipio × semana epidemiológica, ejecuta XGBoost y genera alertas automáticamente.

## Fuentes de Datos Abiertos

| Fuente | Dataset | Tipo |
|--------|---------|------|
| IDEAM — Humedad del aire | [uext-mhny](https://www.datos.gov.co/resource/uext-mhny) | API Socrata |
| IDEAM — Temperatura | [sbwg-7ju4](https://www.datos.gov.co/resource/sbwg-7ju4) | API Socrata |
| IDEAM — Precipitación | [s54a-sgyg](https://www.datos.gov.co/resource/s54a-sgyg) | API Socrata |
| IDEAM — Presión atmosférica | [62tk-nxj5](https://www.datos.gov.co/resource/62tk-nxj5) | API Socrata |
| SISAIRE — PM2.5 | [g4t8-zkc3](https://www.datos.gov.co/resource/g4t8-zkc3) | API Socrata |
| SIVIGILA/INS | Eventos IRA 2018-2023 | Archivo anual |
| DANE — ECV Antioquia 2023 | Encuesta de Calidad de Vida | Archivo |
| DANE — Proyecciones CNPV 2018 | Población 2018-2042 | Archivo |
| DANE — MGN 2025 | Geometrías municipales | GeoJSON |

## Instalación y Ejecución Local

### Prerrequisitos
- Python 3.12+
- Docker y Docker Compose
- Git

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/IsaksGir4/VitalRiskIA.git
cd VitalRiskIA

# 2. Crear archivo .env en la raíz
cat > .env << EOF
DB_USER=vitalrisk_user
DB_PASSWORD=vitalrisk2026
DB_NAME=vitalrisk_db
EOF

# 3. Levantar PostgreSQL + PostGIS
docker-compose up -d db

# 4. Crear entorno virtual e instalar dependencias
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\Activate.ps1  # Windows PowerShell

pip install -r backend/requirements.txt
pip install streamlit folium streamlit-folium altair requests

# 5. Cargar datos iniciales en la base de datos
python etl/load_to_db.py

# 6. Ejecutar el backend (terminal 1)
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 7. Ejecutar el frontend (terminal 2)
cd frontend
streamlit run app.py

# 8. Ejecutar el ETL para datos 2026 (una vez)
# Abrir http://localhost:8000/docs
# POST /api/v1/etl/sincronizar?dias_atras=14
```

### URLs Locales
- **Frontend:** http://localhost:8501
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc

## Índice Preventivo Territorial (IPT)

El IPT es una métrica compuesta que mide la vulnerabilidad de cada municipio ante brotes respiratorios:

```
IPT = 0.40 × percentil(tasa_ira_100k)
    + 0.30 × percentil(pm25_avg)
    + 0.15 × percentil(ipm_pct)
    + 0.15 × percentil(hacinamiento)
```

**Clasificación:** BAJO (0-33) · MEDIO (33-66) · ALTO (66-100)

El IPT y las alertas del modelo son **señales complementarias**: el IPT mide vulnerabilidad estructural del territorio, mientras que las alertas miden desviación de la predicción XGBoost vs la media histórica del municipio.

## Estructura del Repositorio

```
VitalRiskIA/
├── RECURSOS/                    # Material de presentación
├── README.md                    # Este archivo
├── LICENSE                      # Licencia MIT
├── .gitignore                   # Exclusiones
├── docker-compose.yml           # PostgreSQL + PostGIS
├── backend/                     # FastAPI + XGBoost + ETL
│   ├── api/v1/endpoints/        # 7 routers (11 endpoints)
│   ├── services/                # ml_service, etl_service, alertas
│   ├── db/                      # database.py, queries.py
│   └── schemas/                 # Pydantic models
├── frontend/                    # Streamlit (5 vistas)
│   ├── views/                   # dashboard, alertas, modelo_ia, opendata
│   └── assets/                  # CSS design system
├── data/
│   ├── models/                  # modelo_xgboost_vitalrisk.pkl
│   ├── processed/               # CSVs limpios + GeoJSON
│   └── raw/                     # Fuentes originales
├── db/init.sql                  # Schema PostgreSQL (7 tablas)
├── etl/load_to_db.py            # Carga inicial idempotente
├── notebooks/                   # 8 Jupyter notebooks (NB01-NB08)
├── docs/                        # Documentación técnica
│   ├── architecture.md          # Diagrama de arquitectura
│   ├── data_dictionary.md       # Diccionario de datos
│   ├── fuentes_datos.md         # Enlaces a fuentes
│   └── conclusiones.md          # Hallazgos y limitaciones
└── tests/                       # Pruebas automatizadas
```

## Metodología

Se siguió **ASUM-ML**, corregido en el ADR-003:

1. **Business Understanding** → Problemática de IRA en Antioquia
2. **Data Understanding** → EDA con 8 notebooks
3. **Data Preparation** → ETL idempotente, schema PostGIS v4
4. **Modeling** → Comparación de 7 algoritmos, selección XGBoost
5. **Evaluation** → Split cronológico, CV temporal, SHAP
6. **Deployment** → FastAPI + Streamlit + ETL near-real-time

## Equipo

| Rol | Integrante |
|-----|-----------|
| Product Owner / Lead Developer | Isaac Camilo Giraldo Gómez |
| Scrum Master / Data Engineer | Luisa Fernanda Giraldo Zuluaga |

**Universidad:** EIA — Ingeniería Administrativa · Ingeniería de Sistemas
**Universidad:** Simon Bolivar Ingeniería Biomedica

## Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE). Los datos utilizados son de dominio público bajo la política de datos abiertos de Colombia.

---

*VitalRisk AI — Porque la salud pública no debería ser reactiva.*
*Equipo 326 | Datos al Ecosistema 2026 — MinTIC / Colombia Digital*
