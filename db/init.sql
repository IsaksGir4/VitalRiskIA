-- 1. Habilitar la extensión espacial PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Crear la tabla base "dim_municipios" para cumplir el Criterio de Aceptación
CREATE TABLE IF NOT EXISTS dim_municipios (
    codigo_dane VARCHAR(5) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    departamento VARCHAR(100) NOT NULL,
    -- Tipo GEOMETRY(MultiPolygon, 4326) para almacenar la forma del mapa usando WGS84
    geometria GEOMETRY(MultiPolygon, 4326) 
);

-- (Opcional pero recomendado): Crear un índice espacial para acelerar las consultas de mapas
CREATE INDEX idx_dim_municipios_geometria ON dim_municipios USING GIST (geometria);