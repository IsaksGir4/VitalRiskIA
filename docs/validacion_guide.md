# Guía de Validación — VitalRisk AI

## Para pares evaluadores y jurado del concurso

Esta guía permite reproducir y validar los resultados del proyecto desde cero en menos de 30 minutos.

---

## Prerrequisitos

- Python 3.12+
- Docker y Docker Compose instalados
- Git instalado
- Conexión a internet (para las APIs Socrata)

---

## Paso 1 — Clonar y configurar

```bash
git clone https://github.com/IsaksGir4/VitalRiskIA.git
cd VitalRiskIA

# Crear archivo de credenciales
cat > .env << EOF
DB_USER=vitalrisk_user
DB_PASSWORD=vitalrisk2026
DB_NAME=vitalrisk_db
EOF

# Instalar dependencias
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\Activate.ps1    # Windows PowerShell

pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

---

## Paso 2 — Levantar la base de datos

```bash
docker-compose up -d db

# Verificar que está corriendo
docker ps  # debe mostrar vitalrisk_db en estado Up
```

---

## Paso 3 — Cargar datos históricos

```bash
python etl/load_to_db.py
```

**Output esperado:**
```
[1/7] Cargando dim_municipios...       ✓ 125 filas
[2/7] Cargando dim_poblacion_anual...  ✓ 3,125 filas
[3/7] Cargando fact_calidad_aire...    ✓ 12,354 filas
[4/7] Cargando fact_eventos_ira...     ✓ 910 filas
[5/7] Cargando fact_riesgo_territorial...  ✓ 910 filas
[6/7] Actualizando ipt_score...        ✓ actualizados
[7/7] Cargando alertas_territoriales...✓ 845 filas
```

Si los conteos difieren en ±5 filas, es normal (reintentos de carga idempotente).

---

## Paso 4 — Verificar el modelo XGBoost

```bash
cd backend
python -c "
import pickle
with open('../data/models/modelo_xgboost_vitalrisk.pkl', 'rb') as f:
    artefacto = pickle.load(f)
print('Features:', artefacto['features'])
print('RMSE test:', artefacto.get('metricas', {}).get('rmse_test', 'ver metricas_modelo.json'))
print('Modelo:', type(artefacto['modelo']).__name__)
"
```

**Output esperado:** 12 features, XGBRegressor, RMSE ≈ 1.74

---

## Paso 5 — Ejecutar el backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Verificar en:** http://localhost:8000/api/v1/health/

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

---

## Paso 6 — Ejecutar el ETL near-real-time

Con el backend corriendo, abrir http://localhost:8000/docs y ejecutar:

```
POST /api/v1/etl/sincronizar?dias_atras=14
```

**Output esperado en el backend:**
```
Total extraído: ~134,000 registros
Municipios procesados: 38
Alertas: {VERDE: 38, NARANJA: 0, ROJA: 0}
```

El número de municipios puede variar entre 30-45 según disponibilidad de estaciones IDEAM activas.

---

## Paso 7 — Ejecutar el frontend

```bash
cd frontend
streamlit run app.py
```

Abrir http://localhost:8501

**Validaciones visuales:**
- [ ] Dashboard carga en menos de 5 segundos
- [ ] Mapa muestra municipios coloreados (verde/naranja/rojo) para 2026-W27
- [ ] KPI "Municipios monitoreados" muestra 103
- [ ] Sección "Transparencia IA" muestra RMSE=1.7399, R²=0.607
- [ ] Descarga CSV de alertas funciona y contiene 845+ filas

---

## Paso 8 — Ejecutar tests automatizados

```bash
cd backend
pytest ../tests/ -v
```

---

## Validación de métricas del modelo

Las métricas del modelo están almacenadas en `data/models/metricas_modelo.json` y son reproducibles ejecutando el notebook `notebooks/07_feature_engineering_slpt.ipynb`.

| Métrica | Valor esperado | Tolerancia |
|---------|---------------|------------|
| RMSE test | 1.7399 | ±0.05 |
| MAE test | 1.0295 | ±0.05 |
| R² test | 0.607 | ±0.02 |
| RMSE naive baseline | 2.0763 | ±0.05 |

---

## Validación de las APIs Socrata

Para confirmar que las fuentes de datos están activas:

```bash
# Temperatura IDEAM — debe retornar 1 registro de Antioquia
curl "https://www.datos.gov.co/resource/sbwg-7ju4.json?departamento=ANTIOQUIA&\$limit=1"

# PM2.5 SISAIRE — debe retornar datos de Antioquia
curl "https://www.datos.gov.co/resource/g4t8-zkc3.json?codigo_departamento=5&msfl_code=PM2.5&\$limit=1"
```

---

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `Connection refused` en :5433 | Docker no está corriendo | `docker-compose up -d db` |
| `Model not found` | .pkl no está en data/models/ | El archivo está en el repo, verificar path |
| ETL retorna 0 registros | Filtro de fecha sin datos | Probar con `dias_atras=90` |
| Mapa todo gris | No hay datos para esa semana/año | Ejecutar ETL primero con semana 27 año 2026 |

---

*Equipo 326 — VitalRisk AI | Datos al Ecosistema 2026*