# ADR 001: Arquitectura Base y Flujo de Datos para VitalRisk AI

**Fecha:** 1 de Junio de 2026  
**Estado:** Aceptado  
**Autores:** Equipo de Desarrollo VitalRisk AI  

## 1. Contexto
El proyecto VitalRisk AI busca consolidar datasets de múltiples fuentes oficiales (SIATA, DANE, SIVIGILA/INS, Datos.gov.vo) para generar un Índice Preventivo Territorial (IPT) de riesgo respiratorio en Colombia. Necesitamos definir las tecnologías base para la persistencia de datos (ETL), la creación de la API y la visualización, considerando que disponemos de un tiempo de desarrollo de 10 semanas (MVP).

## 2. Decisión Arquitectónica y Justificaciones

### 2.1 Backend: FastAPI sobre Flask
Se ha decidido utilizar **FastAPI** como framework para la capa de servicios web, descartando alternativas tradicionales como Flask.
* **Justificación:** FastAPI incluye validación nativa de datos mediante Pydantic, lo cual es crítico para asegurar la calidad del dato que entra y sale hacia los modelos predictivos. Además, su naturaleza asíncrona (ASGI) maneja mejor las peticiones de mapas interactivos, y genera automáticamente documentación OpenAPI/Swagger (vital para cumplir nuestra Epica 7 de defensa del proyecto).

### 2.2 Base de Datos: PostgreSQL/PostGIS sobre MongoDB
Se ha decidido utilizar **PostgreSQL con la extensión PostGIS** como motor de base de datos principal, descartando bases de datos NoSQL como MongoDB.
* **Justificación:** Nuestro sistema requiere cruzar datos epidemiológicos con polígonos territoriales (municipios) del DANE y coordenadas del SIATA. PostGIS permite realizar "Spatial Joins" (uniones geoespaciales) de forma nativa e incluye algoritmos de simplificación (Douglas-Peucker) directamente en SQL. MongoDB carece de la madurez y eficiencia relacional requerida para modelos de series temporales combinados con geometrías complejas.

## 3. Diagrama de Flujo de Datos (C4 - Nivel Contenedor)

El siguiente diagrama ilustra el flujo de información, desde las fuentes crudas hasta el usuario final.

```mermaid
graph TD
    %% Fuentes de Datos
    subgraph Fuentes de Datos [Datos Abiertos Colombia]
        A1[SIATA - Calidad del Aire]
        A2[DANE - Limites Territoriales]
        A3[INS - Casos IRA]
    end

    %% Capa ETL
    subgraph Ingeniería de Datos [Scripts ETL Python]
        B1[Ingesta Raw]
        B2[Limpieza Pandas]
        B3[Cruce Espacial & Winsorización]
        B1 --> B2 --> B3
    end

    %% Persistencia
    subgraph Base de Datos [Docker Container]
        C1[(PostgreSQL + PostGIS)]
    end

    %% Capa de Negocio
    subgraph Backend [Docker Container]
        D1(FastAPI)
        D2[Motor IPT]
        D3[Modelo XGBoost ML]
    end

    %% Frontend
    subgraph Presentación [Docker Container]
        E1[Streamlit Dashboard Web-GIS]
    end

    %% Relaciones
    A1 -->|API/CSV| B1
    A2 -->|GeoJSON| B1
    A3 -->|CSV| B1
    
    B3 -->|SQLAlchemy Load| C1
    
    C1 <-->|Queries Espaciales / GeoJSON| D1
    D1 <-->|Calculos Z-Score| D2
    D1 <-->|Inferencia| D3
    
    D1 -->|JSON/GeoJSON payload| E1
```

### Consecuencias
* **Positivas:** Aseguramos integridad relacional, alto rendimiento en peticiones espaciales y un entorno altamente tipado gracias a FastAPI.

* **Riesgos:** La curva de aprendizaje de consultas SQL espaciales (PostGIS) puede ser más alta inicialmete, lo cual mitigaremos apoyándonos en la documentación oficial y herramientas como GeoAlchemy.