"""Dashboard territorial — mapa coroplético + KPIs + alertas.

FIX v3: 
- Single GeoJson layer (not 125 individual) → 10x faster
- Colors injected into GeoJSON properties → no lambda closure issues
- Stronger border color so municipalities are always visible
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
    Path(__file__).parent.parent.parent
    / "data" / "processed" / "clean_municipios.geojson"
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
            timeout=10,
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
        return "#CBD5E1"  # slate-300 — visible on light basemap
    if ipt < 33:
        return "#22C55E"  # green-500
    if ipt < 66:
        return "#F59E0B"  # amber-500
    return "#EF4444"      # red-500


@st.cache_data(ttl=60)
def _build_enriched_geojson(anio, semana):
    """Merge API data into base GeoJSON and pre-compute colors.
    
    Returns a single FeatureCollection with _fill_color, _has_alert,
    and display properties baked into each feature. This avoids 125
    separate GeoJson() calls in Folium.
    """
    geo_base = _geojson_base()
    geo_api = _datos_mapa(anio, semana)
    alrts = _alertas()

    # Build lookups
    lookup = {}
    if geo_api and geo_api.get("features"):
        for feat in geo_api["features"]:
            p = feat["properties"]
            cod = str(p.get("codigo_dane", "")).zfill(5)
            lookup[cod] = p

    mun_alerta = {a["codigo_dane"]: a for a in alrts.get("alertas", [])}

    # KPI accumulators
    ipt_vals, va_ipt, pm25_vals, casos_total = [], [], [], 0

    # Enrich each feature
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

        # KPI accumulation
        if ipt is not None:
            ipt_vals.append(ipt)
            if cod in VALLE_ABURRA:
                va_ipt.append(ipt)
        c = _safe(d.get("casos_ira_total"))
        if c:
            casos_total += int(c)
        if pm25:
            pm25_vals.append(pm25)

        # Bake display props into feature
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
            # Tooltip text
            "_tip": (
                f"{nom} ({sub})\n"
                f"IPT: {ipt:.1f} · {nivel}\n" if ipt is not None else f"{nom} ({sub})\nIPT: sin datos\n"
            ) + (
                f"Casos IRA: {casos}\n" if casos != "—" else ""
            ) + (
                f"PM2.5: {pm25:.1f} µg/m³\n" if pm25 else ""
            ) + (
                f"⚠ {al['nivel_alerta']}" if al else ""
            ),
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

    # KPI summary
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

    # Topbar
    st.markdown(f"""
    <div class='topbar'>
        <div class='topbar-model'>
            <div class='topbar-dot'></div>
            Modelo en línea · predicción:
            <strong style='color:#1A2332;margin-left:4px;'>{anio}-W{semana:02d}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load all data in one cached call
    with st.spinner("Cargando datos territoriales..."):
        enriched_geojson, alrts, kpis = _build_enriched_geojson(anio, semana)

    # Title
    st.markdown("""
    <p class='page-title'>Panorama territorial · Antioquia</p>
    <p class='page-subtitle'>
        Predicción semanal (t+1) por municipio ·
        XGBoost + calidad del aire + señales socioeconómicas
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

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
                "Prueba cambiando la semana o el año en el sidebar."
            )
        elif n_con < 20:
            st.caption(
                f"{n_con} de 125 municipios con datos para esta semana. "
                "El resto se muestra en gris."
            )

        # Inline legend
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

        # Build map — ONE GeoJson layer, not 125
        # --- NUEVA LÓGICA DE MAPA OPTIMIZADA ---
        m = folium.Map(location=ANTIOQUIA_CENTER, zoom_start=ANTIOQUIA_ZOOM, tiles="CartoDB positron")

        mun_alerta = {a["codigo_dane"]: a["nivel_alerta"] for a in alrts.get("alertas", [])}

        if enriched_geojson and enriched_geojson.get("features"):
            # 1. Definir función de estilo única (arregla el bug del color blanco)
            def get_style(feature):
                ipt = feature["properties"].get("ipt_score")
                return {
                    "fillColor": _color_ipt(ipt),
                    "color": "#1A2332", # Borde oscuro para que se vean bien
                    "weight": 1,
                    "fillOpacity": 0.75
                }

            # 2. Agregar UNA SOLA CAPA en lugar de 125 iteraciones (Rendimiento extremo)
            folium.GeoJson(
                enriched_geojson,
                style_function=get_style,
                tooltip=folium.GeoJsonTooltip(
                    fields=["nombre", "ipt_score", "nivel_riesgo", "casos_ira_total"],
                    aliases=["Municipio:", "IPT Score:", "Nivel de Riesgo:", "Casos IRA:"],
                    localize=True,
                    style="font-family: sans-serif; font-size: 13px; font-weight: bold;"
                )
            ).add_to(m)

            # 3. Solo iteramos para poner los íconos de advertencia en los municipios en alerta
            for feat in enriched_geojson["features"]:
                cod = feat["properties"].get("codigo_dane")
                al = mun_alerta.get(cod)
                if al:
                    try:
                        geom = feat["geometry"]
                        coords = geom["coordinates"][0][0] if geom["type"] == "MultiPolygon" else geom["coordinates"][0]
                        lat_c = sum(c[1] for c in coords) / len(coords)
                        lon_c = sum(c[0] for c in coords) / len(coords)
                        color_icon = "red" if al == "ALERTA_ROJA" else "orange"
                        folium.Marker(
                            [lat_c, lon_c],
                            icon=folium.DivIcon(
                                html=f'<div style="font-size:18px;color:{color_icon}; text-shadow: 1px 1px 2px black;">⚠</div>',
                                icon_size=(20,20), icon_anchor=(10,10)
                            ),
                            tooltip=f"⚠ {al} — {feat['properties'].get('nombre')}"
                        ).add_to(m)
                    except Exception:
                        pass

            # Leyenda
            folium.Element("""
            <div style='position:fixed;bottom:24px;left:24px;z-index:9999;
                        background:white;padding:10px 14px;border-radius:6px;
                        border:1px solid #ddd;font-family:sans-serif;font-size:12px;
                        box-shadow:2px 2px 6px rgba(0,0,0,0.15)'>
                <b>IPT — Riesgo</b><br>
                <span style='color:#375623; font-size:16px;'>■</span> BAJO (0-33)<br>
                <span style='color:#FFC000; font-size:16px;'>■</span> MEDIO (33-66)<br>
                <span style='color:#C00000; font-size:16px;'>■</span> ALTO (66-100)<br>
                <span style='color:#AAAAAA; font-size:16px;'>■</span> Sin datos<br>
                <span style='color:red; font-size:16px;'>⚠</span> Alerta activa
            </div>
            """).add_to(m.get_root().html)

        # Usar width="stretch" para quitar la advertencia amarilla
        st_folium(m, height=500, width="stretch", returned_objects=[])

    # Alerts panel
    with col_panel:
        st.markdown(
            "<div class='section-title'>Alertas recientes</div>",
            unsafe_allow_html=True,
        )
        alertas_list = alrts.get("alertas", [])
        if alertas_list:
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
                            <div class='pred-label'>Δ histórico</div>
                            <div class='pred-value {"pred-delta-pos" if desv > 0 else "pred-delta-neg"}'>{desv:+.1f}%</div>
                        </div>
                    </div>
                    <div class='causal-tag'>{var}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='empty-state'>
                <div class='empty-state-icon'>🟢</div>
                <div class='empty-state-title'>Territorio seguro</div>
                <div class='empty-state-text'>
                    No hay alertas preventivas activas en este período.<br>
                    Todos los municipios están dentro de los rangos esperados.
                </div>
            </div>
            """, unsafe_allow_html=True)