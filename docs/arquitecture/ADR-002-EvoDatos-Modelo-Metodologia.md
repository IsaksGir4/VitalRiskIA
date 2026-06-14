# ADR 002: Evolución del Ecosistema de Datos, Modelado PostGIS y Metodología ASUM-ML
**Fecha:** 13 de Junio de 2026
**Estado:** Aceptado
**Autores:** Equipo de Desarrollo VitalRisk AI
**Relación:** Complementa a ADR 001 (Arquitectura Base) y ADR 002 (CRISP-ML).

## 1. Contexto
Durante el Sprint 2 del proyecto VitalRisk AI, la complejidad de las fuentes de datos ha aumentado significativamente. Pasamos de 3 fuentes genéricas a más de 10 fuentes específicas (que incluyen mediciones horarias del IDEAM, proyecciones poblacionales y datos socioeconómicos de la Encuesta de Calidad de Vida de Antioquia). Adicionalmente, necesitamos establecer un flujo de trabajo claro que separe la **exploración científica (EDA)** de la **automatización productiva (ETL).**

## 2. Decisiones Arquitectónicas y Justificaciones
### 2.1 Flujo de Trabajo Híbrido basado en ASUM-ML
Se ha decidido adoptar el marco de trabajo **ASUM-ML** para el ciclo de vida de los datos, dividiendo el trabajo en dos entornos físicos:

**Fases de Descubrimiento y Diseño (EDA):** Se realizarán prototipos en Jupyter Notebooks usando GeoPandas y Pandas. Aquí se manejarán valores nulos, winsorización y validación de esquemas (SIVIGILA).

**Fases de Implementación y Despliegue:** El código validado en los Notebooks será refactorizado y encapsulado en scripts modulares de Python (.py) que formarán el pipeline ETL automatizado e idempotente.

**Justificación:** Previene que código espagueti de análisis llegue a producción, asegurando que el pipeline del Backend sea determinista, rápido y fácil de testear (TDD).

### 2.2 Modelado Analítico Desnormalizado (Feature Store)
La base de datos PostGIS no seguirá una **Tercera Forma Normal (3NF) estricta**. Se utilizará un esquema de 7 tablas divididas en dimensiones (catálogos) y hechos (series de tiempo).

- **Dimensiones:** dim_municipios, dim_estaciones_aire, dim_poblacion_anual.

- **Hechos y Analítica:** fact_calidad_aire, fact_eventos_ira, fact_riesgo_territorial, alertas_territoriales.

**Justificación:** Para alimentar el modelo seleccionado, la velocidad de lectura es prioritaria sobre el espacio en disco. Separar dim_poblacion_anual nos permite calcular de forma precisa las tasas de IRA históricas por cada 100,000 habitantes.

### 2.3 Estrategia de Contingencia de Fuentes (Fallback Plan)
Existe una restricción de 3 a 10 datasets para el concurso. Se ha emitido una solicitud formal al SIATA para obtener un dataset unificado histórico de PM2.5, PM10 y variables meteorológicas.

**Decisión:** Se utilizarán las APIs fragmentadas del IDEAM (Temperatura, Precipitación, Presión, Humedad) temporalmente durante la fase de EDA. Si el SIATA aprueba la solicitud, estas fuentes del IDEAM serán reemplazadas por el dataset unificado del SIATA en el pipeline final ETL.

**Justificación:** Esta estrategia de mitigación de riesgos asegura que el desarrollo del modelo seleccionado no se bloquee por dependencias externas, al tiempo que garantiza el cumplimiento del límite máximo de datasets impuesto por el concurso.

## 3. Diagrama de Flujo de Datos Actualizado (Data Pipeline)
El siguiente diagrama ilustra la evolución de la ingesta y transformación de datos, reflejando las nuevas fuentes y el ciclo ASUM-ML.

```mermaid
graph TD
    %% ZONA BRONCE: Fuentes de Datos Crudos
    subgraph Fuentes de Datos (Raw / Zona Bronce)
        A1[SIATA - Dataset Unificado / API Contingencia IDEAM]
        A2[DANE - DIVIPOLA GeoJSON]
        A3[DANE - Proyecciones Población]
        A4[INS - Histórico SIVIGILA IRA]
        A5[Gobernación - ECV Antioquia]
    end

    %% ZONA PLATA: ASUM-ML Análisis
    subgraph Entorno de Descubrimiento (Jupyter Notebooks)
        B1(01_exploracion_IRA_ESI.ipynb)
        B2(02_exploracion_clima_ideam_siata.ipynb)
        B3(03_exploracion_dane_geometria.ipynb)
    end

    %% ZONA ORO: ETL Productivo
    subgraph Pipeline ETL (Python Scripts)
        C1[Extract: request & batch download]
        C2[Transform: merge, clean, winsorize]
        C3[Load: SQLAlchemy to PostGIS]
        C1 --> C2 --> C3
    end

    %% Persistencia Base de Datos Completa
    subgraph Feature Store (PostGIS)
        D1[(dim_municipios)]
        D2[(dim_estaciones_aire)]
        D3[(dim_poblacion_anual)]
        D4[(fact_calidad_aire)]
        D5[(fact_eventos_ira)]
        D6[(fact_riesgo_territorial)]
        D7[(alertas_territoriales)]
    end

    %% Relaciones
    A1 & A2 & A3 & A4 & A5 -->|Ingesta Exploratoria| B1
    A1 & A2 & A3 & A4 & A5 -->|Ingesta Automatizada| C1
    
    B1 & B2 & B3 -.->|Refactorización de Código| C2
    
    C3 -->|SQL Insert/Upsert| D1
    C3 -->|SQL Insert/Upsert| D2
    C3 -->|SQL Insert/Upsert| D3
    C3 -->|SQL Insert/Upsert| D4
    C3 -->|SQL Insert/Upsert| D5
    C3 -->|SQL Insert/Upsert| D6
    C3 -->|SQL Insert/Upsert| D7
```
## 4. Consecuencias
**Positivas:** El equipo tiene un límite claro entre experimentación (Jupyter) y producción (Scripts). Las tablas de la base de datos están alineadas exactamente con la infraestructura aprovisionada. El riesgo de exceder el límite de datasets está mitigado.

**Riesgos:** Mantener la sincronía de código entre un Notebook y un Script de Python requiere disciplina. Se mitigará usando revisiones de código (Code Reviews) obligatorias en Jira antes de pasar una tarea a la columna "Done".