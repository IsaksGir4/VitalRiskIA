"""Dashboard territorial — mapa coroplético + KPIs + alertas.

Optimización v4:
- Single GeoJson layer (not 125 individual) for 10x performance
- Colors injected into GeoJSON properties
- Hero banner dinámico que resume el estado territorial al abrir
"""
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import json
import math
from pathlib import Path
from config import API

GEOJSON_PATH = (
    Path(__file__).parent.parent
    / "data" / "processed" / "clean_municipios_simple.geojson"
)

VALLE_ABURRA = {
    "05001", "05088", "05129", "05212", "05266",
    "05308", "05360", "05380", "05631", "05079",
}

ANTIOQUIA_CENTER = [6.85, -75.65]
ANTIOQUIA_ZOOM = 7


@st.cache_data(ttl=600)
def _geojson_base():
    if not GEOJSON_PATH.exists():
        return {"type": "FeatureCollection", "features": []}
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=60)
def _datos_mapa(anio, semana):
    try:
        r = requests.get(
            f"{API}/mapa/riesgo",
            params={"anio": anio, "semana_epi": semana},
            timeout=30,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


@st.cache_data(ttl=300)
def _alertas():
    try:
        r = requests.get(f"{API}/alertas/activas", timeout=10)
        return r.json() if r.status_code == 200 else {"alertas": [], "total": 0}
    except Exception:
        return {"alertas": [], "total": 0}


def _safe(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return None


def _color_ipt(ipt):
    """Map IPT score to fill color."""
    if ipt is None:
        return "#CBD5E1"
    if ipt < 33:
        return "#22C55E"
    if ipt < 66:
        return "#F59E0B"
    return "#EF4444"


@st.cache_data(ttl=60)
def _build_enriched_geojson(anio, semana):
    """Merge API data into base GeoJSON and pre-compute colors."""
    geo_base = _geojson_base()
    geo_api = _datos_mapa(anio, semana)
    alrts = _alertas()

    lookup = {}
    if geo_api and geo_api.get("features"):
        for feat in geo_api["features"]:
            p = feat["properties"]
            cod = str(p.get("codigo_dane", "")).zfill(5)
            lookup[cod] = p

    mun_alerta = {a["codigo_dane"]: a for a in alrts.get("alertas", [])}

    ipt_vals, va_ipt, pm25_vals, casos_total = [], [], [], 0

    enriched_features = []
    for feat in geo_base.get("features", []):
        props = feat["properties"]
        cod = str(props.get("codigo_dane", "")).zfill(5)
        nom = props.get("nombre", cod)
        sub = props.get("subregion", "")

        d = lookup.get(cod, {})
        ipt = _safe(d.get("ipt_score"))
        nivel = d.get("nivel_riesgo", "—")
        casos = d.get("casos_ira_total", "—")
        pm25 = _safe(d.get("pm25_avg"))
        tasa = _safe(d.get("tasa_ira_100k"))
        al = mun_alerta.get(cod)

        if ipt is not None:
            ipt_vals.append(ipt)
            if cod in VALLE_ABURRA:
                va_ipt.append(ipt)
        c = _safe(d.get("casos_ira_total"))
        if c:
            casos_total += int(c)
        if pm25:
            pm25_vals.append(pm25)

        new_props = {
            "codigo_dane": cod,
            "nombre": nom,
            "subregion": sub,
            "ipt_score": ipt,
            "nivel_riesgo": nivel,
            "casos_ira_total": casos,
            "pm25_avg": pm25,
            "tasa_ira_100k": tasa,
            "_fill_color": _color_ipt(ipt),
            "_has_alert": al is not None,
            "_alert_nivel": al["nivel_alerta"] if al else "",
        }

        enriched_features.append({
            "type": "Feature",
            "geometry": feat["geometry"],
            "properties": new_props,
        })

    enriched_geojson = {
        "type": "FeatureCollection",
        "features": enriched_features,
    }

    n_rojas = sum(1 for a in alrts.get("alertas", []) if a["nivel_alerta"] == "ALERTA_ROJA")
    n_naranjas = sum(1 for a in alrts.get("alertas", []) if a["nivel_alerta"] == "ALERTA_NARANJA")
    kpis = {
        "ipt_prom": sum(ipt_vals) / len(ipt_vals) if ipt_vals else None,
        "ipt_va": sum(va_ipt) / len(va_ipt) if va_ipt else None,
        "pm25_p": sum(pm25_vals) / len(pm25_vals) if pm25_vals else None,
        "n_con_datos": len(lookup),
        "n_rojas": n_rojas,
        "n_naranjas": n_naranjas,
        "total_alertas": alrts.get("total", 0),
    }

    return enriched_geojson, alrts, kpis


def render(anio: int, semana: int):

    with st.spinner("Cargando datos territoriales..."):
        enriched_geojson, alrts, kpis = _build_enriched_geojson(anio, semana)

    # ── Hero banner dinámico ──────────────────────────────
    # Cambia de color y mensaje según el estado real del territorio
    n_rojas = kpis["n_rojas"]
    n_naranjas = kpis["n_naranjas"]
    total_al = kpis["total_alertas"]

    if n_rojas > 0:
        hero_bg = "linear-gradient(135deg, #DC2626 0%, #991B1B 100%)"
        hero_icon = "!"
        hero_title = f"{n_rojas} municipio{'s' if n_rojas > 1 else ''} en alerta crítica"
        hero_sub = (f"{n_naranjas} adicional{'es' if n_naranjas > 1 else ''} en monitoreo · "
                    f"Semana epidemiológica {semana:02d} de {anio}")
    elif n_naranjas > 0:
        hero_bg = "linear-gradient(135deg, #D97706 0%, #92400E 100%)"
        hero_icon = "!"
        hero_title = f"{n_naranjas} municipio{'s' if n_naranjas > 1 else ''} en monitoreo"
        hero_sub = f"Sin alertas críticas · Semana epidemiológica {semana:02d} de {anio}"
    else:
        hero_bg = "linear-gradient(135deg, #16A34A 0%, #15803D 100%)"
        hero_icon = "&#10003;"
        hero_title = "Territorio en rango normal"
        hero_sub = f"103 municipios monitoreados · Semana epidemiológica {semana:02d} de {anio}"

    st.markdown(f"""
    <div style='background:{hero_bg};border-radius:0;padding:20px 24px;
                margin-bottom:16px;display:flex;align-items:center;gap:16px;'>
        <div style='width:44px;height:44px;background:rgba(255,255,255,0.2);
                    border-radius:10px;display:flex;align-items:center;
                    justify-content:center;font-size:1.3rem;font-weight:700;
                    color:white;'>{hero_icon}</div>
        <div>
            <div style='font-size:1.2rem;font-weight:700;color:white;
                        line-height:1.3;'>{hero_title}</div>
            <div style='font-size:0.82rem;color:rgba(255,255,255,0.85);
                        margin-top:2px;'>{hero_sub}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    kpi_data = [
        (c1, "Municipios monitoreados", "103",
         "Cobertura total Antioquia", "#1A5F7A"),
        (c2, "IPT promedio Antioquia",
         f"{kpis['ipt_prom']:.1f}" if kpis["ipt_prom"] else "—",
         "Índice Preventivo Territorial", "#1A5F7A"),
        (c3, "IPT Valle de Aburrá",
         f"{kpis['ipt_va']:.1f}" if kpis["ipt_va"] else "—",
         "Foco subregional del proyecto", "#16A34A"),
        (c4, "Alertas activas", str(kpis["total_alertas"]),
         f"{kpis['n_rojas']} críticas · {kpis['n_naranjas']} monitoreo",
         "#DC2626" if kpis["n_rojas"] > 0 else "#1A5F7A"),
        (c5, "PM2.5 promedio",
         f"{kpis['pm25_p']:.1f} µg/m³" if kpis["pm25_p"] else "—",
         "Material particulado fino (IDEAM)", "#1A5F7A"),
    ]
    for col, label, val, hint, color in kpi_data:
        with col:
            st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>{label}</div>
                <div class='kpi-value' style='color:{color};'>{val}</div>
                <div class='kpi-hint'>{hint}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Map + Alerts panel
    col_mapa, col_panel = st.columns([3, 1])

    with col_mapa:
        st.markdown(
            "<div class='section-title'>Mapa de riesgo territorial</div>",
            unsafe_allow_html=True,
        )

        n_con = kpis["n_con_datos"]
        if n_con == 0:
            st.warning(
                f"No hay datos en la API para {anio}-W{semana:02d}. "
                "Cambia la semana o el año en el panel lateral."
            )
        elif n_con < 20:
            st.caption(
                f"{n_con} de 125 municipios con datos para esta semana. "
                "El resto se muestra en gris."
            )

        # Leyenda inline
        st.markdown("""
        <div style='display:inline-flex;align-items:center;gap:14px;
                    font-size:0.78rem;color:#64748B;margin-bottom:6px;'>
            <span><span style='display:inline-block;width:12px;height:12px;
                  border-radius:3px;background:#22C55E;margin-right:4px;
                  vertical-align:middle;'></span>BAJO (0–33)</span>
            <span><span style='display:inline-block;width:12px;height:12px;
                  border-radius:3px;background:#F59E0B;margin-right:4px;
                  vertical-align:middle;'></span>MEDIO (33–66)</span>
            <span><span style='display:inline-block;width:12px;height:12px;
                  border-radius:3px;background:#EF4444;margin-right:4px;
                  vertical-align:middle;'></span>ALTO (66–100)</span>
            <span><span style='display:inline-block;width:12px;height:12px;
                  border-radius:3px;background:#CBD5E1;margin-right:4px;
                  vertical-align:middle;'></span>Sin datos</span>
        </div>
        """, unsafe_allow_html=True)

        # Build map — ONE GeoJson layer
        m = folium.Map(
            location=ANTIOQUIA_CENTER,
            zoom_start=ANTIOQUIA_ZOOM,
            tiles="CartoDB positron",
        )

        mun_alerta = {
            a["codigo_dane"]: a["nivel_alerta"]
            for a in alrts.get("alertas", [])
        }

        if enriched_geojson and enriched_geojson.get("features"):
            def get_style(feature):
                ipt = feature["properties"].get("ipt_score")
                return {
                    "fillColor": _color_ipt(ipt),
                    "color": "#1A2332",
                    "weight": 1,
                    "fillOpacity": 0.75,
                }

            folium.GeoJson(
                enriched_geojson,
                style_function=get_style,
                tooltip=folium.GeoJsonTooltip(
                    fields=["nombre", "ipt_score", "nivel_riesgo", "casos_ira_total"],
                    aliases=["Municipio:", "IPT:", "Nivel:", "Casos IRA:"],
                    localize=True,
                    style="font-family:sans-serif;font-size:13px;font-weight:bold;",
                ),
            ).add_to(m)

            # Marcadores de alerta (solo municipios con alerta activa)
            for feat in enriched_geojson["features"]:
                cod = feat["properties"].get("codigo_dane")
                al = mun_alerta.get(cod)
                if al:
                    try:
                        geom = feat["geometry"]
                        coords = (
                            geom["coordinates"][0][0]
                            if geom["type"] == "MultiPolygon"
                            else geom["coordinates"][0]
                        )
                        lat_c = sum(c[1] for c in coords) / len(coords)
                        lon_c = sum(c[0] for c in coords) / len(coords)
                        color_icon = "red" if al == "ALERTA_ROJA" else "orange"
                        folium.Marker(
                            [lat_c, lon_c],
                            icon=folium.DivIcon(
                                html=(
                                    f'<div style="font-size:16px;color:{color_icon};'
                                    f'text-shadow:1px 1px 2px rgba(0,0,0,0.5);'
                                    f'font-weight:bold;">!</div>'
                                ),
                                icon_size=(20, 20),
                                icon_anchor=(10, 10),
                            ),
                            tooltip=f"{al.replace('ALERTA_', '')} — {feat['properties'].get('nombre')}",
                        ).add_to(m)
                    except Exception:
                        pass

            # Leyenda dentro del mapa
            folium.Element("""
            <div style='position:fixed;bottom:24px;left:24px;z-index:9999;
                        background:white;padding:10px 14px;border-radius:6px;
                        border:1px solid #ddd;font-family:sans-serif;font-size:12px;
                        box-shadow:2px 2px 6px rgba(0,0,0,0.15)'>
                <b>IPT — Nivel de riesgo</b><br>
                <span style='color:#22C55E;font-size:14px;'>&#9632;</span> BAJO (0–33)<br>
                <span style='color:#F59E0B;font-size:14px;'>&#9632;</span> MEDIO (33–66)<br>
                <span style='color:#EF4444;font-size:14px;'>&#9632;</span> ALTO (66–100)<br>
                <span style='color:#CBD5E1;font-size:14px;'>&#9632;</span> Sin datos<br>
                <b style='color:red;'>!</b> Alerta activa
            </div>
            """).add_to(m.get_root().html)

        st_folium(m, height=500, width="stretch", returned_objects=[])

    # Panel derecho: alertas activas O municipios a vigilar
    with col_panel:
        alertas_list = alrts.get("alertas", [])
        if alertas_list:
            # Hay alertas → mostrar detalle de cada una
            st.markdown(
                "<div class='section-title'>Alertas activas</div>",
                unsafe_allow_html=True,
            )
            for a in alertas_list[:8]:
                nivel = a["nivel_alerta"]
                cls = "danger" if "ROJA" in nivel else "watch" if "NARANJA" in nivel else "normal"
                lab = nivel.replace("ALERTA_", "")
                desv = a.get("desviacion_pct") or 0
                pred = a.get("prediccion_casos") or 0
                var = a.get("variable_causal", "N/D")
                nom = a.get("nombre", a["codigo_dane"])

                st.markdown(f"""
                <div class='alerta-card {cls}'>
                    <div style='display:flex;justify-content:space-between;
                                align-items:flex-start;margin-bottom:6px;'>
                        <div class='alerta-municipio'>{nom}</div>
                        <span class='nivel-badge {cls}'>{lab}</span>
                    </div>
                    <div class='pred-grid'>
                        <div>
                            <div class='pred-label'>Pred. t+1</div>
                            <div class='pred-value'>{pred:.1f}</div>
                        </div>
                        <div>
                            <div class='pred-label'>Desviación</div>
                            <div class='pred-value {"pred-delta-pos" if desv > 0 else "pred-delta-neg"}'>{desv:+.1f}%</div>
                        </div>
                    </div>
                    <div class='causal-tag'>Causa: {var}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Sin alertas → mostrar municipios con IPT más alto (vigilancia preventiva)
            st.markdown(
                "<div class='section-title'>Municipios a vigilar</div>",
                unsafe_allow_html=True,
            )
            st.caption("Mayor IPT este período — sin alerta activa")

            mun_ipt = []
            for feat in enriched_geojson.get("features", []):
                p = feat["properties"]
                ipt_val = p.get("ipt_score")
                if ipt_val is not None:
                    mun_ipt.append({
                        "nombre": p.get("nombre", ""),
                        "subregion": p.get("subregion", ""),
                        "ipt": ipt_val,
                        "nivel": p.get("nivel_riesgo", ""),
                        "casos": p.get("casos_ira_total", "—"),
                    })

            mun_ipt.sort(key=lambda x: x["ipt"], reverse=True)

            for mi in mun_ipt[:6]:
                ipt_v = mi["ipt"]
                if ipt_v >= 66:
                    cls = "danger"
                elif ipt_v >= 33:
                    cls = "watch"
                else:
                    cls = "normal"

                st.markdown(f"""
                <div class='alerta-card {cls}'>
                    <div style='display:flex;justify-content:space-between;
                                align-items:flex-start;margin-bottom:4px;'>
                        <div>
                            <div class='alerta-municipio'>{mi['nombre']}</div>
                            <div class='alerta-sub'>{mi['subregion']}</div>
                        </div>
                        <span class='nivel-badge {cls}'>{mi['nivel']}</span>
                    </div>
                    <div class='pred-grid'>
                        <div>
                            <div class='pred-label'>IPT</div>
                            <div class='pred-value'>{ipt_v:.1f}</div>
                        </div>
                        <div>
                            <div class='pred-label'>Casos IRA</div>
                            <div class='pred-value'>{mi['casos']}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)