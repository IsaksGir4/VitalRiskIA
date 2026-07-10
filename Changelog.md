# Changelog — VitalRisk AI

Todos los cambios relevantes del proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [1.0.0] — 2026-07-06

### Agregado
- ETL Near-Real-Time conectado a 5 APIs Socrata de datos.gov.co (IDEAM + SISAIRE)
- Endpoint `POST /api/v1/etl/sincronizar` para ejecutar pipeline bajo demanda
- PM2.5 integrado desde SISAIRE (g4t8-zkc3) con fallback a datos más recientes
- Cálculo de IPT real con fórmula de percentiles ponderados
- Población proyectada DANE hasta 2042 para cálculo de tasa_ira_100k
- Frontend con 5 vistas: Dashboard, Alertas, Perfil, Datos Abiertos, Transparencia IA
- Mapa coroplético Folium con capa GeoJSON única (optimización de rendimiento)
- Empty state "Territorio seguro" cuando no hay alertas activas
- Predicción en vivo con 1 clic (solo municipio + semana + año)
- Portal de datos abiertos estilo SaluData con descargas CSV
- Transparencia IA con métricas XGBoost, feature importance y justificaciones técnicas
- 11 endpoints REST documentados en Swagger/OpenAPI
- README.md, LICENSE MIT, .gitignore

### Corregido
- Colores del mapa (de blanco a verde/naranja/rojo visible)
- Sidebar labels con contraste insuficiente en modo oscuro
- Tema forzado a claro via config.toml
- `use_container_width` reemplazado por `width="stretch"` (deprecación Streamlit)
- Encoding UTF-8 para lectura de CSS en Windows
- Endpoint `/opendata/alertas` usaba columnas de IPT en vez de alertas

## [0.9.0] — 2026-07-01

### Agregado
- Modelo XGBoost entrenado: RMSE=1.7399, R²=0.607 (test 2022-2023)
- 807 alertas territoriales generadas con SHAP TreeExplainer
- Base de datos PostGIS con 7 tablas y schema v4
- Script ETL idempotente (load_to_db.py)
- Backend FastAPI con endpoints de mapa, alertas, predicción, opendata, modelo
- Docker Compose para PostgreSQL + PostGIS

## [0.5.0] — 2026-06-25

### Agregado
- 8 Jupyter notebooks (NB01-NB08) con pipeline CRISP-ML completo
- EDA, limpieza, feature engineering, selección de features (6 métodos)
- Comparación de 7 algoritmos de regresión
- IPT calculado para 103 municipios × 6 años
- Documentación ADR-001, ADR-002, ADR-003
- GeoJSON de 125 municipios de Antioquia con datos socioeconómicos

## [0.1.0] — 2026-06-15

### Agregado
- Configuración inicial del proyecto
- Docker Compose con PostGIS
- Estructura de carpetas del repositorio
- Registro en Jira como Equipo 326
