import csv
import io
import math
from utils import normalizar_texto
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from settings.dependencies import get_db
from db.queries import get_opendata_ipt, get_opendata_alertas

router = APIRouter()

# 1. Aplicación del principio DRY: Centralizamos la función de limpieza
def clean_value(v):
    """Convierte None, NaN e Inf a cadena vacía de forma segura."""
    if v is None:
        return ""
    try:
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return ""
    except Exception:
        pass
    return v

@router.get("/ipt", tags=["Datos Abiertos"],
            summary="Descarga IPT completo como CSV")
def descargar_ipt(db: Session = Depends(get_db)):
    rows = get_opendata_ipt(db)

    def generate():
        # Buffer e instanciación única (Eficiencia O(1) en memoria)
        buf = io.StringIO()
        buf.write('\ufeff') # BOM para Excel (tildes correctas)
        writer = csv.writer(buf, lineterminator='\n') # Evita doble salto de línea
        
        writer.writerow([
            "codigo_dane","nombre","subregion","anio","semana_epi",
            "fecha_semana","ipt_score","nivel_riesgo","casos_ira_total",
            "tasa_ira_100k","pm25_avg","humedad_avg","temperatura_avg",
            "periodo_pandemia"
        ])
        yield buf.getvalue().encode("utf-8")
        
        # Limpiamos el buffer para entrar al bucle
        buf.seek(0)
        buf.truncate(0)

        for row in rows:
            writer.writerow([
                str(row.codigo_dane).zfill(5),
                normalizar_texto(clean_value(row.nombre)),
                normalizar_texto(clean_value(row.subregion)),
                row.anio,
                row.semana_epi,
                clean_value(row.fecha_semana),
                clean_value(row.ipt_score),
                clean_value(row.nivel_riesgo),
                clean_value(row.casos_ira_total),
                clean_value(row.tasa_ira_100k),
                clean_value(row.pm25_avg),
                clean_value(row.humedad_avg),
                clean_value(row.temperatura_avg),
                row.periodo_pandemia
            ])
            yield buf.getvalue().encode("utf-8")
            
            # Limpiamos el buffer en cada iteración
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                "attachment; filename=vitalrisk_ipt_antioquia_2018_2023.csv"
        }
    )

@router.get("/alertas", tags=["Datos Abiertos"],
            summary="Descarga historial de alertas como CSV")
def descargar_alertas(db: Session = Depends(get_db)):
    rows = get_opendata_alertas(db)

    def generate():
        buf = io.StringIO()
        buf.write('\ufeff')
        writer = csv.writer(buf, lineterminator='\n')
        
        writer.writerow([
            "codigo_dane","nombre","subregion","anio","semana_epi",
            "nivel_alerta","prediccion_casos","desviacion_pct",
            "variable_causal","media_historica","fecha_generacion"
        ])
        yield buf.getvalue().encode("utf-8")
        
        buf.seek(0)
        buf.truncate(0)

        for row in rows:
            # Tu fix de mapeo de columnas está perfecto aquí
            writer.writerow([
                str(row.codigo_dane).zfill(5),
                normalizar_texto(clean_value(row.nombre)),
                normalizar_texto(clean_value(row.subregion)),
                row.anio,
                row.semana_epi,
                clean_value(row.nivel_alerta),
                clean_value(row.prediccion_casos),
                clean_value(row.desviacion_pct),
                clean_value(row.variable_causal),
                clean_value(row.media_historica),
                clean_value(row.fecha_generacion)
            ])
            yield buf.getvalue().encode("utf-8")
            
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                "attachment; filename=vitalrisk_alertas_antioquia_2018_2023.csv"
        }
    )

@router.get(
    "/metadatos/ipt",
    tags=["Datos Abiertos"],
    summary="Diccionario de datos del IPT"
)
def metadatos_ipt():
    """
    Retorna el diccionario de datos y metadatos del Índice Preventivo
    Territorial.
    """
    return {
        "nombre_conjunto": "Índice Preventivo Territorial (IPT) — Antioquia 2018-2023",
        "descripcion": (
            "Dataset combinado de casos IRA (SIVIGILA/INS), calidad del aire "
            "(IDEAM SISAIRE+DHIME) y datos socioeconómicos (DANE ECV Antioquia 2023) "
            "para predicción de brotes respiratorios con una semana de anticipación."
        ),
        "fuente_datos": {
            "epidemiologica": "SIVIGILA — Instituto Nacional de Salud (INS) 2018-2023",
            "ambiental":      "IDEAM — SISAIRE (PM2.5/PM10) + DHIME (clima)",
            "socioeconomica": "DANE — ECV Antioquia 2023 + Proyecciones CNPV 2018",
            "geometria":      "DANE — MGN2025 (polígonos municipales)"
        },
        "cobertura": {
            "territorial": "103 municipios de Antioquia con registro epidemiológico",
            "temporal":    "2018-2023 (semanas epidemiológicas 1-52)",
            "registros":   910
        },
        "periodicidad": "Semanal (semana epidemiológica INS)",
        "ultima_actualizacion": "2026-07-01",
        "licencia": "Datos Abiertos Colombia — Dominio Público",
        "responsable": "VitalRisk AI — Equipo 326 | Datos al Ecosistema 2026",
        "variables": [
            {"nombre": "codigo_dane",     "tipo": "VARCHAR(5)",
             "descripcion": "Código DIVIPOLA de 5 dígitos del municipio"},
            {"nombre": "semana_epi",      "tipo": "INTEGER",
             "descripcion": "Semana epidemiológica (1-52) según calendario INS"},
            {"nombre": "ipt_score",       "tipo": "NUMERIC",
             "descripcion": "Índice Preventivo Territorial (0-100). Calculado como combinación ponderada de percentiles: 40% tasa_ira_100k + 30% pm25_avg + 15% ipm_pct + 15% icv_hacinamiento"},
            {"nombre": "nivel_riesgo",    "tipo": "VARCHAR",
             "descripcion": "Clasificación del IPT: BAJO (<33), MEDIO (33-66), ALTO (>66)"},
            {"nombre": "casos_ira_total", "tipo": "INTEGER",
             "descripcion": "Casos de IRA (J00-J22 CIE-10) notificados por el municipio esa semana"},
            {"nombre": "tasa_ira_100k",   "tipo": "NUMERIC",
             "descripcion": "Tasa de incidencia de IRA por 100,000 habitantes. Denominador: proyección DANE del año correspondiente"},
            {"nombre": "pm25_avg",        "tipo": "NUMERIC",
             "descripcion": "Concentración promedio semanal de PM2.5 (µg/m³). 2018-2019: imputado desde Promedio Anual IDEAM. 2020-2023: SISAIRE directo"},
            {"nombre": "periodo_pandemia","tipo": "BOOLEAN",
             "descripcion": "TRUE para 2020-03-01 a 2021-12-31. Flag metodológico que indica período COVID-19 — no descartar, usar como variable de control"}
        ],
        "nota_metodologica": (
            "El período pandemia (2020-2021) está marcado con periodo_pandemia=TRUE "
            "y no fue excluido del análisis. Se usó como variable de control en el "
            "modelo XGBoost, permitiéndole aprender que ese período fue una perturbación "
            "externa extraordinaria. Es una fortaleza metodológica, no una limitación."
        )
    }