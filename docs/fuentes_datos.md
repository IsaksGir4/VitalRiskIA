# Fuentes de Datos — VitalRisk AI

## APIs Socrata Conectadas (ETL Near-Real-Time)

| # | Variable | ID Socrata | URL de Acceso | Protocolo |
|---|----------|-----------|---------------|-----------|
| 1 | Humedad del aire | uext-mhny | https://www.datos.gov.co/resource/uext-mhny.json | SODA2 |
| 2 | Temperatura ambiente | sbwg-7ju4 | https://www.datos.gov.co/resource/sbwg-7ju4.json | SODA2 |
| 3 | Precipitación | s54a-sgyg | https://www.datos.gov.co/resource/s54a-sgyg.json | SODA2 |
| 4 | Presión atmosférica | 62tk-nxj5 | https://www.datos.gov.co/resource/62tk-nxj5.json | SODA2 |
| 5 | PM2.5 (SISAIRE) | g4t8-zkc3 | https://www.datos.gov.co/resource/g4t8-zkc3.json | SODA2 |

**Documentación SODA2:** https://dev.socrata.com/

## Archivos Estáticos (Carga Inicial)

| # | Fuente | Archivo | Registros | Período |
|---|--------|---------|-----------|---------|
| 1 | SIVIGILA/INS | clean_ira_2018_2023.csv | 910 | 2018-2023 |
| 2 | DANE ECV Antioquia 2023 | clean_municipios.csv | 125 | 2023 |
| 3 | DANE Proyecciones CNPV | clean_poblacion_anual.csv | 3,125 | 2018-2042 |
| 4 | DANE MGN 2025 | clean_municipios.geojson | 125 | 2025 |
| 5 | IDEAM SISAIRE (NB02) | clean_calidad_aire.csv | 12,354 | 2018-2023 |

## Portales de Datos Abiertos Utilizados

- **datos.gov.co** — Portal Nacional de Datos Abiertos de Colombia
- **datos.siata.gov.co** — Sistema de Alerta Temprana del Valle de Aburrá (respaldo PM2.5)
- **www.ins.gov.co** — Instituto Nacional de Salud (eventos SIVIGILA)
- **www.dane.gov.co** — Departamento Administrativo Nacional de Estadística

## Cobertura de Datos

- **Territorial:** 103 municipios de Antioquia con registro epidemiológico (125 en geometrías)
- **Temporal:** 2018-2023 histórico + 2026 en tiempo real
- **Estaciones IDEAM activas en Antioquia:** 38 municipios con al menos 1 estación
- **Granularidad:** Semana epidemiológica (calendario INS) × municipio
