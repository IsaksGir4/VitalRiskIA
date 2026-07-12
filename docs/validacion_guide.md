# Guía de Validación — VitalRisk AI

## Para pares evaluadores y jurado del concurso

Esta guía permite reproducir y validar los resultados del proyecto desde cero. Tiene dos rutas: **Ruta A** (producción en la nube, sin instalar nada) y **Ruta B** (local con Docker, reproducibilidad completa).

---

## 🌐 Ruta A — Validación remota en producción (5 minutos)

No requiere instalación. El sistema está desplegado en:

| Servicio | URL |
|---|---|
| **Dashboard (Frontend)** | https://vitalriskia-frontend.onrender.com |
| **API REST (Backend)** | https://vitalriskia.onrender.com |
| **Swagger / Documentación** | https://vitalriskia.onrender.com/docs |

> ⚠️ **Cold start:** Render pausa el servicio tras inactividad. La primera petición puede tardar 30–60 segundos. Si el mapa tarda en cargar, espera y recarga.

### Checklist de validación remota

- [ ] El dashboard carga y muestra el mapa de Antioquia coloreado por IPT
- [ ] Los tooltips del mapa muestran nombre del municipio, IPT, casos IRA y PM2.5
- [ ] La sección "Transparencia IA" muestra RMSE=1.7399 y R²=0.607
- [ ] La descarga CSV desde "Datos Abiertos" funciona y contiene filas con datos reales
- [ ] `GET https://vitalriskia.onrender.com/api/v1/health/` responde `{"status": "OK", "dependencias": {"base_de_datos": "OK", "modelo_xgboost": "OK", "features_modelo": 12}}`

### Validar las APIs Socrata (fuentes de datos)

```bash
# IDEAM Temperatura — debe retornar 1 registro de Antioquia
curl "https://www.datos.gov.co/resource/sbwg-7ju4.json?Departamento=ANTIOQUIA&\$limit=1"

# IDEAM PM2.5 SISAIRE — debe retornar datos de Antioquia
curl "https://www.datos.gov.co/resource/g4t8-zkc3.json?codigo_departamento=5&msfl_code=PM2.5&\$limit=1"
```

---

## 🖥️ Ruta B — Validación local con Docker (30 minutos)

### Prerrequisitos

- Python 3.12+
- Docker y Docker Compose
- Git

### Paso 1 — Clonar y configurar

```bash
git clone https://github.com/IsaksGir4/VitalRiskIA.git
cd VitalRiskIA

# Opción A: conda
conda env create -f environment.yml
conda activate vitalrisk

# Opción B: pip
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt

# Crear archivo de credenciales locales
cp .env.example .env
# Editar .env con DB_HOST=127.0.0.1, DB_PORT=5433 y tus credenciales
```

### Paso 2 — Levantar la base de datos

```bash
docker-compose up -d db

# Verificar que está corriendo
docker ps  # debe mostrar vitalrisk_db en estado Up (healthy)
```

### Paso 3 — Cargar datos históricos

```bash
python etl/load_to_db.py
```

**Output esperado:**

```
[1/7] Cargando dim_municipios...           ✓ 125 filas
[2/7] Cargando dim_poblacion_anual...      ✓ 3,125 filas
[3/7] Cargando fact_calidad_aire...        ✓ 12,354 filas
[4/7] Cargando fact_eventos_ira...         ✓ 910 filas
[5/7] Cargando fact_riesgo_territorial...  ✓ 910 filas
[6/7] Actualizando ipt_score...            ✓ actualizados
[7/7] Cargando alertas_territoriales...    ✓ 845 filas
```

Si los conteos difieren en ±10 filas es normal (idempotencia del upsert).

### Paso 4 — Verificar el modelo XGBoost

```bash
python -c "
import pickle, json
from pathlib import Path

with open('data/models/modelo_xgboost_vitalrisk.pkl', 'rb') as f:
    artefacto = pickle.load(f)

metricas = json.load(open('data/models/metricas_modelo.json'))
print('Tipo de modelo:', type(artefacto[\"modelo\"]).__name__)
print('Features:', artefacto['features'])
print('RMSE test:', metricas.get('rmse_test', 'ver metricas_modelo.json'))
print('R2 test:  ', metricas.get('r2_test'))
"
```

**Output esperado:** XGBRegressor · 12 features · RMSE ≈ 1.7399 · R² ≈ 0.607

### Paso 5 — Ejecutar el backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Verificar en:** `http://localhost:8000/api/v1/health/`

**Output esperado:**
```json
{
  "status": "OK",
  "dependencias": {
    "base_de_datos": "OK",
    "modelo_xgboost": "OK",
    "features_modelo": 12
  }
}
```

### Paso 6 — Ejecutar el ETL near-real-time

Con el backend corriendo, ejecutar desde Swagger (`http://localhost:8000/docs`) o con curl:

```bash
curl -X POST "http://localhost:8000/api/v1/etl/sincronizar?dias_atras=14"
```

**Output esperado en los logs del backend:**
```
── FASE 1: EXTRACT ──
  → humedad_avg (uext-mhny)...    ~25,000 registros
  → temperatura_avg (sbwg-7ju4)... ~25,000 registros
  → precipitacion_sum (s54a-sgyg)... ~50,000 registros
  → presion_avg (62tk-nxj5)...    ~23,000 registros
  → pm25_avg (histórico BD)...    75 municipios
── FASE 3: LOAD + PREDICT ──
  Municipios procesados: 38
  Alertas generadas: {VERDE: 38, NARANJA: 0, ROJA: 0}
```

El número de municipios varía entre 30–45 según disponibilidad de estaciones IDEAM activas. Las alertas tienden a VERDE porque SIVIGILA 2026 no tiene API pública — el modelo usa la media histórica como proxy (desviación ≈ 0%).

### Paso 7 — Ejecutar el frontend

```bash
cd frontend
streamlit run app.py
```

Abrir `http://localhost:8501`

**Validaciones visuales:**
- [ ] Mapa muestra municipios coloreados (verde/naranja/rojo) para el año y semana actuales
- [ ] KPI "Municipios monitoreados" muestra 103
- [ ] KPI "IPT Valle de Aburrá" muestra un valor entre 0 y 100
- [ ] Sección "Transparencia IA" muestra RMSE=1.7399, R²=0.607
- [ ] Descarga CSV en "Datos Abiertos" contiene 845+ filas con encabezados correctos

### Paso 8 — Ejecutar tests automatizados

```bash
pytest tests/ -v
```

---

## Validación de métricas del modelo

Las métricas están en `data/models/metricas_modelo.json` y son reproducibles ejecutando `notebooks/07_feature_engineering_slpt.ipynb` completo.

| Métrica | Valor esperado | Tolerancia |
|---------|---------------|------------|
| RMSE test (2022-2023) | 1.7399 | ±0.05 |
| MAE test | 1.0295 | ±0.05 |
| R² test | 0.607 | ±0.02 |
| RMSE naive baseline | 2.0763 | ±0.05 |
| Mejora vs naive | +16.2% | ±1% |
| Features en el modelo | 12 | exacto |

---

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `Connection refused` en :5433 | Docker no está corriendo | `docker-compose up -d db` |
| `Model not found` | `.pkl` no está en `data/models/` | Verificar que el archivo existe: `ls data/models/` |
| ETL retorna 0 registros meteorológicos | Rango de fechas sin datos | Probar con `dias_atras=90` |
| Mapa todo gris | No hay datos para esa semana/año | Ejecutar el ETL primero |
| Cold start timeout en Render | Servicio pausado por inactividad | Esperar 60 s y recargar |
| `AttributeError: fetch_sisaire_pm25` | Versión desactualizada del código | Hacer `git pull` para obtener el fix |

---

## Estructura de datos para reproducibilidad

Los datos procesados están en `data/processed/` y pueden verificarse contra las fuentes originales en `data/raw/`:

| Archivo | Filas | Fuente verificable |
|---------|-------|--------------------|
| `clean_ira_2018_2023.csv` | 910 | datos.gov.co · INS SIVIGILA evento 345 |
| `clean_calidad_aire.csv` | 12,354 | datos.gov.co · IDEAM SISAIRE + DHIME |
| `clean_municipios.geojson` | 125 | geoportal.dane.gov.co · MGN2025 |
| `clean_poblacion_anual.csv` | 3,125 | dane.gov.co · CNPV 2018 proyecciones |
| `fact_riesgo_territorial_ipt.csv` | 910 | Generado por NB04-NB06 |
| `alertas_territoriales.csv` | 845+ | Generado por NB08 |

---

*Equipo 326 — VitalRisk AI | Datos al Ecosistema 2026*