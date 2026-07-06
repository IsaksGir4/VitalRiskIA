from sqlalchemy.orm import Session
from sqlalchemy import text

def get_media_historica_municipio(db: Session, codigo_dane: str) -> float:
    row = db.execute(text("""
        SELECT AVG(casos_ira_total) AS media
        FROM fact_riesgo_territorial
        WHERE codigo_dane = :cod AND periodo_pandemia = FALSE
    """), {"cod": codigo_dane}).fetchone()
    return float(row.media) if row and row.media else 3.0

def get_media_historica_semana(
        db: Session, codigo_dane: str, semana_epi: int) -> float:
    row = db.execute(text("""
        SELECT AVG(casos_ira_total) AS media
        FROM fact_riesgo_territorial
        WHERE codigo_dane = :cod
          AND semana_epi  = :sem
          AND anio BETWEEN 2018 AND 2020
    """), {"cod": codigo_dane, "sem": semana_epi}).fetchone()
    return float(row.media) if row and row.media else None

def get_municipio(db: Session, codigo_dane: str):
    return db.execute(
        text("SELECT nombre, subregion FROM dim_municipios "
             "WHERE codigo_dane = :cod"),
        {"cod": codigo_dane}
    ).fetchone()

def get_alertas_activas(db: Session, nivel: str = None):
    filtro = ("AND a.nivel_alerta = :nivel" if nivel
              else "AND a.nivel_alerta IN ('ALERTA_ROJA','ALERTA_NARANJA')")
    params = {"nivel": nivel} if nivel else {}
    return db.execute(text(f"""
        SELECT a.codigo_dane, m.nombre, m.subregion,
               a.anio, a.semana_epi, a.nivel_alerta,
               a.prediccion_casos, a.desviacion_pct,
               a.variable_causal, a.media_historica
        FROM alertas_territoriales a
        JOIN dim_municipios m ON a.codigo_dane = m.codigo_dane
        WHERE (a.anio, a.semana_epi) = (
            SELECT anio, semana_epi FROM alertas_territoriales
            ORDER BY anio DESC, semana_epi DESC LIMIT 1
        )
        {filtro}
        ORDER BY
            CASE a.nivel_alerta
                WHEN 'ALERTA_ROJA'    THEN 1
                WHEN 'ALERTA_NARANJA' THEN 2
                ELSE 3
            END,
            a.desviacion_pct DESC
    """), params).fetchall()

def get_alertas_municipio(
        db: Session, codigo_dane: str, anio: int = None):
    filtro = "AND a.anio = :anio" if anio else ""
    params = {"cod": codigo_dane}
    if anio:
        params["anio"] = anio
    return db.execute(text(f"""
        SELECT a.anio, a.semana_epi, a.nivel_alerta,
               a.prediccion_casos, a.desviacion_pct,
               a.variable_causal, a.media_historica
        FROM alertas_territoriales a
        WHERE a.codigo_dane = :cod {filtro}
        ORDER BY a.anio DESC, a.semana_epi DESC
    """), params).fetchall()

def get_mapa_riesgo_anual(db: Session, anio: int):
    return db.execute(text("""
        SELECT m.codigo_dane, m.nombre, m.subregion,
               :anio AS anio,
               ROUND(AVG(r.ipt_score)::numeric, 2)     AS ipt_score,
               MODE() WITHIN GROUP (ORDER BY r.nivel_riesgo) AS nivel_riesgo,
               SUM(r.casos_ira_total)                   AS casos_ira_total,
               ROUND(AVG(r.tasa_ira_100k)::numeric, 4)  AS tasa_ira_100k,
               ROUND(AVG(r.pm25_avg)::numeric, 3)       AS pm25_avg,
               ST_AsGeoJSON(m.geometria)::json           AS geometry
        FROM dim_municipios m
        JOIN fact_riesgo_territorial r ON m.codigo_dane = r.codigo_dane
        WHERE r.anio = :anio AND m.geometria IS NOT NULL
        GROUP BY m.codigo_dane, m.nombre, m.subregion, m.geometria
        ORDER BY m.nombre
    """), {"anio": anio}).fetchall()

def get_mapa_riesgo_semana(db: Session, anio: int, semana_epi: int):
    return db.execute(text("""
        SELECT m.codigo_dane, m.nombre, m.subregion,
               r.semana_epi, r.anio,
               r.ipt_score, r.nivel_riesgo,
               r.casos_ira_total, r.tasa_ira_100k, r.pm25_avg,
               ST_AsGeoJSON(m.geometria)::json AS geometry
        FROM dim_municipios m
        JOIN fact_riesgo_territorial r ON m.codigo_dane = r.codigo_dane
        WHERE r.anio = :anio AND r.semana_epi = :sem
          AND m.geometria IS NOT NULL
        ORDER BY m.nombre
    """), {"anio": anio, "sem": semana_epi}).fetchall()

def get_resumen_municipio(db: Session, codigo_dane: str):
    return db.execute(text("""
        SELECT m.nombre, m.subregion,
               m.icv_score, m.ipm_pct, m.icv_seg_social,
               m.icv_hacinamiento, m.nbi,
               ROUND(AVG(r.ipt_score)::numeric, 2)  AS ipt_promedio,
               SUM(r.casos_ira_total)                AS casos_totales,
               ROUND(AVG(r.pm25_avg)::numeric, 3)    AS pm25_promedio,
               COUNT(r.id)                           AS semanas_registradas
        FROM dim_municipios m
        LEFT JOIN fact_riesgo_territorial r ON m.codigo_dane = r.codigo_dane
        WHERE m.codigo_dane = :cod
        GROUP BY m.codigo_dane, m.nombre, m.subregion,
                 m.icv_score, m.ipm_pct, m.icv_seg_social,
                 m.icv_hacinamiento, m.nbi
    """), {"cod": codigo_dane}).fetchone()

def get_opendata_ipt(db: Session):
    return db.execute(text("""
        SELECT r.codigo_dane, m.nombre, m.subregion,
               r.anio, r.semana_epi, r.fecha_semana,
               r.ipt_score, r.nivel_riesgo,
               r.casos_ira_total, r.tasa_ira_100k,
               r.pm25_avg, r.humedad_avg, r.temperatura_avg,
               r.periodo_pandemia
        FROM fact_riesgo_territorial r
        JOIN dim_municipios m ON r.codigo_dane = m.codigo_dane
        ORDER BY r.anio, r.semana_epi, m.nombre
    """)).fetchall()

def get_opendata_alertas(db: Session):
    return db.execute(text("""
        SELECT a.codigo_dane, m.nombre, m.subregion,
               a.anio, a.semana_epi,
               a.nivel_alerta, a.prediccion_casos,
               a.desviacion_pct, a.variable_causal,
               a.media_historica, a.fecha_generacion
        FROM alertas_territoriales a
        JOIN dim_municipios m ON a.codigo_dane = m.codigo_dane
        ORDER BY a.anio DESC, a.semana_epi DESC, a.nivel_alerta
    """)).fetchall()
def get_ultima_semana_disponible(db: Session):
    """Obtiene el último año y semana epidemiológica registrados."""
    row = db.execute(text("""
        SELECT anio, semana_epi
        FROM fact_riesgo_territorial
        ORDER BY anio DESC, semana_epi DESC
        LIMIT 1
    """)).fetchone()
    return {"anio": int(row.anio), "semana_epi": int(row.semana_epi)} if row else None