# Resolución: PostgreSQL en Docker no acepta conexiones desde Windows

## Síntoma
psycopg2.OperationalError: connection to server at "localhost" port 5432 failed:
FATAL: password authentication failed for user "vitalrisk_user"

## Causa raíz

PostgreSQL instalado nativamente en Windows y Docker comparten el puerto 5432.
El PostgreSQL nativo intercepta las conexiones antes de que lleguen al contenedor.

## Diagnóstico

```powershell
# Verificar si hay dos procesos en el puerto 5432
netstat -ano | findstr :5432

# Identificar los procesos
Get-Process -Id <PID1>
Get-Process -Id <PID2>
```

Si ves un proceso `postgres` y otro `com.docker.backend`, el conflicto está confirmado.

---

## Solución: cambiar el puerto del contenedor

### 1. Actualizar `docker-compose.yml`

```yaml
db:
  image: postgis/postgis:14-3.3
  ports:
    - "5433:5432"    # ← cambiar de 5432:5432 a 5433:5432
  environment:
    - POSTGRES_USER=${DB_USER}
    - POSTGRES_PASSWORD=${DB_PASSWORD}
    - POSTGRES_DB=${DB_NAME}
    - POSTGRES_HOST_AUTH_METHOD=trust
```

### 2. Actualizar `.env`

```env
DB_USER=vitalrisk_user
DB_PASSWORD=tu_password
DB_NAME=vitalrisk_db
DB_PORT=5433
```

### 3. Reiniciar contenedores

```powershell
docker-compose down
docker-compose up -d
```

### 4. Verificar conexión

```powershell
python -c "
import psycopg2
conn = psycopg2.connect(
    host='127.0.0.1',
    port=5433,
    dbname='vitalrisk_db',
    user='vitalrisk_user',
    password='tu_password'
)
print('Conexion exitosa')
"
```

### 5. Actualizar `load_to_db.py`

```python
DB_URL = (
    f"postgresql://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@127.0.0.1:"
    f"{os.getenv('DB_PORT', '5433')}/"
    f"{os.getenv('DB_NAME')}"
)
```

---

## Errores adicionales al cargar datos

### Error: `Geometry type (Polygon) does not match column type (MultiPolygon)`

Algunos municipios tienen geometría `Polygon` pero la columna espera `MultiPolygon`.
Usar `ST_Multi()` en el UPDATE para convertir automáticamente:

```python
with engine.begin() as conn:
    for _, row in gdf_geo.iterrows():
        conn.execute(text("""
            UPDATE dim_municipios
            SET geometria = ST_Multi(ST_GeomFromText(:wkt, 4326))
            WHERE codigo_dane = :cod
        """), {"wkt": row['geometry'].wkt, "cod": row['codigo_dane']})
```

### Error: `integer out of range`

Las columnas lag (`casos_ira_lag1`, `casos_ira_total`) llegan como `float64`
con valores `NaN` que PostgreSQL no puede convertir a `INTEGER`.

```python
# Convertir antes de cargar
df['casos_ira_lag1'] = df['casos_ira_lag1'].astype('Int64')
df['casos_ira_total'] = df['casos_ira_total'].astype('Int64')
df = df.where(pd.notna(df), other=None)
```

---

## Verificación final

```powershell
docker exec -it vitalrisk_db psql -U vitalrisk_user -d vitalrisk_db -c "
SELECT schemaname, tablename, n_live_tup
FROM pg_stat_user_tables
ORDER BY tablename;
"
```

Resultado esperado:

| tablename                | n_live_tup |
|--------------------------|------------|
| dim_municipios           | 125        |
| dim_poblacion_anual      | 750        |
| fact_calidad_aire        | 12,354     |
| fact_eventos_ira         | 910        |
| fact_riesgo_territorial  | 910        |