# Fuentes de Datos — VitalRisk AI

## APIs Socrata Conectadas (ETL Near-Real-Time)

Las siguientes APIs se consultan automáticamente vía `POST /api/v1/etl/sincronizar`. Protocolo: SODA2. Sin autenticación requerida (con App Token opcional para mayor rate limit).

| # | Variable | ID Socrata | URL directa | Registros típicos (14 días) |
|---|----------|-----------|-------------|---------------------------|
| 1 | Humedad del aire | `uext-mhny` | [datos.gov.co/resource/uext-mhny](https://www.datos.gov.co/resource/uext-mhny) | ~25,000 |
| 2 | Temperatura ambiente | `sbwg-7ju4` | [datos.gov.co/resource/sbwg-7ju4](https://www.datos.gov.co/resource/sbwg-7ju4) | ~25,000 |
| 3 | Precipitación | `s54a-sgyg` | [datos.gov.co/resource/s54a-sgyg](https://www.datos.gov.co/resource/s54a-sgyg) | ~50,000 |
| 4 | Presión atmosférica | `62tk-nxj5` | [datos.gov.co/resource/62tk-nxj5](https://www.datos.gov.co/resource/62tk-nxj5) | ~23,000 |
| 5 | PM2.5 / PM10 (SISAIRE) | `g4t8-zkc3` | [datos.gov.co/resource/g4t8-zkc3](https://www.datos.gov.co/resource/g4t8-zkc3) | Histórico BD (rezago > 1 año) |

**Documentación SODA2:** https://dev.socrata.com/

**Nota sobre PM2.5:** SISAIRE tiene rezago de actualización de > 1 año. El ETL usa el promedio histórico de `fact_calidad_aire` como proxy para el período reciente. Cuando SISAIRE publique actualizaciones, el pipeline las incorpora automáticamente sin cambios de código.

---

## Archivos Estáticos (Carga Inicial — `etl/load_to_db.py`)

| # | Tabla destino | Archivo | Filas | Período | Portal |
|---|---|---|---|---|---|
| 1 | `fact_eventos_ira` | `clean_ira_2018_2023.csv` | 910 | 2018-2023 | INS / SIVIGILA evento 345 |
| 2 | `dim_municipios` | `clean_municipios.geojson` | 125 | Estático 2025 | geoportal.dane.gov.co · MGN2025 |
| 3 | `dim_poblacion_anual` | `clean_poblacion_anual.csv` | 3,125 | 2018-2042 | dane.gov.co · CNPV 2018 |
| 4 | `fact_calidad_aire` | `clean_calidad_aire.csv` | 12,354 | 2018-2023 | datos.gov.co · IDEAM SISAIRE + DHIME |
| 5 | `fact_riesgo_territorial` | `fact_riesgo_territorial_ipt.csv` | 910 | 2018-2023 | Generado por pipeline (NB04-NB06) |
| 6 | `alertas_territoriales` | `alertas_territoriales.csv` | 845+ | 2018-2023 | Generado por modelo XGBoost (NB08) |

---

## Portales de Datos Abiertos Utilizados

| Portal | Entidad | Uso en el proyecto |
|--------|---------|-------------------|
| [datos.gov.co](https://www.datos.gov.co) | MinTIC / Gobierno de Colombia | 5 APIs Socrata (variables climáticas y PM2.5) |
| [ins.gov.co](https://www.ins.gov.co/buscador-eventos/Paginas/sivigila.aspx) | Instituto Nacional de Salud | Archivos SIVIGILA anuales — evento 345 (IRA) |
| [antioquiadatos.gov.co](https://www.antioquiadatos.gov.co/estadisticasAntioquia/encuestaCalidadVida) | Gobernación de Antioquia | ECV 2023 — 9 indicadores socioeconómicos |
| [geoportal.dane.gov.co](https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/?cod=111) | DANE | MGN2025 — geometrías de 125 municipios |
| [dane.gov.co](https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion) | DANE | Proyecciones poblacionales CNPV 2018 (2018-2042) |

---

## Fuente Pendiente

| Fuente | Estado | Mitigación aplicada |
|--------|--------|---------------------|
| **SIATA** — histórico unificado PM2.5 | Radicado 021682 registrado el 2026-06-09. Sin respuesta al cierre del proyecto. | Plan B IDEAM ejecutado completo. Pipeline preparado para integrar datos SIATA sin cambios de código cuando estén disponibles. |
| **SIVIGILA 2025-2026** | No tiene API Socrata pública con datos recientes. Los archivos anuales se publican con rezago. | El modelo usa media histórica municipal como proxy. Las alertas reflejarán desviaciones reales en cuanto existan datos SIVIGILA recientes. |

---

## Cobertura Territorial y Temporal

| Dimensión | Cobertura |
|-----------|-----------|
| Municipios con geometría | 125 (todos los de Antioquia) |
| Municipios con registro IRA | 103 (con al menos un caso en 2018-2023) |
| Municipios con estación IDEAM | 38 (con datos climáticos directos) |
| Período histórico | 2018-2023 (6 años, 52 semanas/año) |
| Período en tiempo real (ETL) | 2026 — actualizable semanalmente |
| Granularidad | Municipio × Semana Epidemiológica |