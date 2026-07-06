"""Alertas preventivas + Predicción en vivo (1 clic).

FIX v3:
- Predicción: usuario solo elige municipio del dropdown → 1 clic
- Empty state atractivo cuando no hay alertas
- El backend llena los datos automáticamente desde la BD
"""
import streamlit as st
import requests
import pandas as pd
from config import API


MUNICIPIOS_VA = {
    "05001": "Medellín",
    "05088": "Bello",
    "05129": "Caldas",
    "05212": "Copacabana",
    "05266": "Envigado",
    "05308": "Girardota",
    "05360": "Itagüí",
    "05380": "La Estrella",
    "05631": "Sabaneta",
    "05079": "Barbosa",
}


@st.cache_data(ttl=300)
def _alertas_activas():
    try:
        r = requests.get(f"{API}/alertas/activas", timeout=10)
        return r.json() if r.status_code == 200 else {"alertas": [], "total": 0}
    except Exception:
        return {"alertas": [], "total": 0}


@st.cache_data(ttl=300)
def _historial(cod, anio):
    try:
        r = requests.get(f"{API}/alertas/{cod}", params={"anio": anio}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def _prediccion_live(cod, semana, anio):
    """Call prediction with only codigo_dane + semana + anio.
    The backend fills missing features from the database automatically."""
    try:
        payload = {"codigo_dane": cod, "semana_epi": semana, "anio": anio}
        r = requests.post(f"{API}/prediccion/", json=payload, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def render(anio: int, semana: int):
    st.markdown("""
    <p class='page-title'>Alertas preventivas</p>
    <p class='page-subtitle'>
        Municipios con desviación significativa sobre la media histórica ·
        Umbral NARANJA: +30% · Umbral ROJO: +60%
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.spinner("Cargando alertas..."):
        data = _alertas_activas()

    alertas = data.get("alertas", [])
    rojas = [a for a in alertas if "ROJA" in a["nivel_alerta"]]
    naranjas = [a for a in alertas if "NARANJA" in a["nivel_alerta"]]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "Alertas críticas (ROJA)", str(len(rojas)), "#DC2626"),
        (c2, "En monitoreo (NARANJA)", str(len(naranjas)), "#D97706"),
        (c3, "Total alertas activas", str(data.get("total", 0)), "#1A5F7A"),
        (c4, "Municipios monitoreados", "103", "#16A34A"),
    ]:
        with col:
            st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>{label}</div>
                <div class='kpi-value' style='color:{color};'>{val}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    tab_alertas, tab_prediccion = st.tabs(["Alertas activas", "Predicción en vivo"])

    # ── Tab: Alertas activas ──────────────────────────────
    with tab_alertas:
        if not alertas:
            st.markdown("""
            <div class='empty-state'>
                <div class='empty-state-icon'>🟢</div>
                <div class='empty-state-title'>Territorio seguro</div>
                <div class='empty-state-text'>
                    No hay alertas preventivas activas en este período.<br>
                    Los 103 municipios monitoreados están dentro de los rangos
                    esperados según el modelo XGBoost.<br><br>
                    <span style='font-size:0.78rem;color:#166534;'>
                        Umbrales: NARANJA &gt; +30% · ROJA &gt; +60% sobre media histórica
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for i in range(0, len(alertas), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j >= len(alertas):
                        break
                    a = alertas[i + j]
                    nivel = a["nivel_alerta"]
                    cls = "danger" if "ROJA" in nivel else "watch" if "NARANJA" in nivel else "normal"
                    lab = nivel.replace("ALERTA_", "")
                    desv = a.get("desviacion_pct") or 0
                    pred = a.get("prediccion_casos") or 0
                    var = a.get("variable_causal", "N/D")
                    media = a.get("media_historica") or 0

                    with col:
                        st.markdown(f"""
                        <div class='alerta-card {cls}'>
                            <div style='display:flex;justify-content:space-between;
                                        align-items:flex-start;margin-bottom:8px;'>
                                <div>
                                    <div class='alerta-municipio'>
                                        {a.get('nombre', a['codigo_dane'])}
                                    </div>
                                    <div class='alerta-sub'>
                                        {a.get('subregion', 'N/D')} ·
                                        Sem. {a.get('semana_epi', '?')}
                                    </div>
                                </div>
                                <span class='nivel-badge {cls}'>{lab}</span>
                            </div>
                            <div class='pred-grid'>
                                <div>
                                    <div class='pred-label'>Predicción t+1</div>
                                    <div class='pred-value'>{pred:.1f}
                                        <span style='font-size:0.7rem;color:#64748B;'>casos</span>
                                    </div>
                                </div>
                                <div>
                                    <div class='pred-label'>Δ vs histórico</div>
                                    <div class='pred-value {"pred-delta-pos" if desv > 0 else "pred-delta-neg"}'>
                                        {desv:+.1f}%
                                    </div>
                                </div>
                            </div>
                            <div style='font-size:0.75rem;color:#64748B;margin-bottom:6px;'>
                                Media histórica: {media:.1f} casos/semana
                            </div>
                            <div class='causal-tag'>Variable causal: {var}</div>
                        </div>
                        """, unsafe_allow_html=True)

    # ── Tab: Predicción en vivo (1 clic) ──────────────────
    # ── Tab 2: Predicción Automática ──────────────────────────
    with tab_prediccion:
        st.markdown(
            "<div class='section-title'>Predicción Automática XGBoost</div>",
            unsafe_allow_html=True
        )
        st.caption("Selecciona un municipio para predecir el comportamiento de la siguiente semana basándose en la data histórica más reciente.")

        col_form, col_result = st.columns([1, 1])

        with col_form:
            with st.form("prediccion_form"):
                # Dropdown de municipios
                mun_elegido = st.selectbox("Seleccionar Municipio", options=list(MUNICIPIOS_VA.keys()), format_func=lambda x: f"{MUNICIPIOS_VA[x]} ({x})")
                
                submit = st.form_submit_button("🔮 Ejecutar Predicción En Vivo", use_container_width=True)

        with col_result:
            if submit:
                with st.spinner("Conectando con XGBoost..."):
                    # Solo enviamos el código y la fecha, el backend autocompleta con datos de la BD o promedios
                    try:
                        payload = {"codigo_dane": mun_elegido, "semana_epi": semana, "anio": anio}
                        r = requests.post(f"{API}/prediccion/", json=payload, timeout=10)
                        result = r.json() if r.status_code == 200 else None
                    except Exception:
                        result = None

                if result:
                    nivel = result.get("nivel_alerta","")
                    cls = "roja" if "ROJA" in nivel else "naranja" if "NARANJA" in nivel else "verde"
                    pred = result.get("prediccion_casos_t1", 0)
                    desv = result.get("desviacion_pct", 0) or 0
                    var = result.get("variable_causal","N/D")

                    st.markdown(f"""
                    <div style='background:white; border-left: 5px solid {"#DC2626" if cls=="roja" else "#D97706" if cls=="naranja" else "#16A34A"}; padding:15px; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1);'>
                        <h3 style='margin:0; color:#1A2332;'>Resultado: {MUNICIPIOS_VA[mun_elegido]}</h3>
                        <p style='font-size:2.5rem; font-weight:bold; margin:10px 0; color:#1A5F7A;'>{pred:.1f} <span style='font-size:1rem; font-weight:normal;'>casos (t+1)</span></p>
                        <p><b>Estado:</b> {nivel.replace('ALERTA_','')}</p>
                        <p><b>Desviación Histórica:</b> {desv:+.1f}%</p>
                        <p style='background:#E8F4F8; padding:5px; border-radius:4px;'><b>Causa principal (SHAP):</b> ⚠ {var}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Error al conectar con la API de predicción.")
            else:
                st.info("👈 Selecciona un municipio y haz clic en Predecir.")


def render_perfil(anio: int, semana: int):
    st.markdown("""
    <p class='page-title'>Perfil epidemiológico por municipio</p>
    <p class='page-subtitle'>Historial de alertas y contexto socioeconómico</p>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        mun_options = {f"{v} ({k})": k for k, v in MUNICIPIOS_VA.items()}
        mun_sel = st.selectbox(
            "Municipio",
            options=list(mun_options.keys()),
            index=0,
            key="perfil_mun",
        )
        cod = mun_options[mun_sel]
    with c2:
        anio_h = st.selectbox(
            "Año", [2023, 2022, 2021, 2020, 2019, 2018], key="perfil_anio"
        )

    if st.button("Ver perfil", type="primary"):
        with st.spinner("Cargando historial..."):
            hist = _historial(cod.zfill(5), anio_h)

        if hist:
            res = hist.get("resumen_alertas", {})
            st.markdown(f"""
            <div style='background:#E8F4F8;border-radius:8px;
                        padding:12px 16px;margin-bottom:14px;
                        border-left:4px solid #1A5F7A;'>
                <strong style='font-size:1rem;color:#1A2332;'>
                    {hist.get('nombre', mun_sel)}
                </strong>
                <span style='font-size:0.8rem;color:#64748B;margin-left:8px;'>
                    {hist.get('total_semanas', 0)} semanas registradas
                </span>
                <div style='margin-top:6px;display:flex;gap:16px;font-size:0.82rem;'>
                    <span style='color:#DC2626;font-weight:600;'>
                        {res.get('ALERTA_ROJA', 0)} críticas
                    </span>
                    <span style='color:#D97706;font-weight:600;'>
                        {res.get('ALERTA_NARANJA', 0)} monitoreo
                    </span>
                    <span style='color:#16A34A;font-weight:600;'>
                        {res.get('ALERTA_VERDE', 0)} normales
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            df = pd.DataFrame(hist.get("alertas", []))
            if not df.empty:
                cols_show = ["semana_epi", "nivel_alerta", "prediccion_casos",
                             "desviacion_pct", "variable_causal", "media_historica"]
                cols_ok = [c for c in cols_show if c in df.columns]

                def color_nivel(val):
                    if val == "ALERTA_ROJA":
                        return "background-color:#FEF2F2;color:#DC2626;font-weight:600"
                    if val == "ALERTA_NARANJA":
                        return "background-color:#FFFBEB;color:#D97706;font-weight:600"
                    return "background-color:#F0FDF4;color:#16A34A;"

                st.dataframe(
                    df[cols_ok].style.map(color_nivel, subset=["nivel_alerta"]),
                    width="stretch",
                    hide_index=True,
                    height=420,
                )
        else:
            st.warning(f"No se encontró historial para {mun_sel}.")