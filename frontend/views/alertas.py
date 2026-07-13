"""Alertas preventivas + Predicción en vivo — layout 2 columnas.

Cambios v4 (sustentación):
- Tabs eliminados → 2 columnas (alertas | predicción) visibles al mismo tiempo
- Emojis casuales reemplazados por indicadores CSS
- Predicción: 1 clic, backend autocompleta features desde BD
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


def render(anio: int, semana: int):
    st.markdown("""
    <p class='page-title'>Alertas preventivas y predicción</p>
    <p class='page-subtitle'>
        Detección de desviaciones significativas sobre la media histórica ·
        Predicción XGBoost en tiempo de consulta
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.spinner("Cargando alertas..."):
        data = _alertas_activas()

    alertas = data.get("alertas", [])
    rojas = [a for a in alertas if "ROJA" in a["nivel_alerta"]]
    naranjas = [a for a in alertas if "NARANJA" in a["nivel_alerta"]]

    # KPIs — sin emojis, colores semánticos
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

    # ── Layout 2 columnas: Alertas activas | Predicción en vivo ──
    col_alertas, col_prediccion = st.columns([1.3, 1])

    # ── Columna izquierda: Alertas activas ────────────────
    with col_alertas:
        st.markdown(
            "<div class='section-title'>Alertas activas</div>",
            unsafe_allow_html=True,
        )
        st.caption("Umbral NARANJA: +30% · ROJA: +60% sobre media histórica")

        if not alertas:
            st.markdown("""
            <div class='empty-state'>
                <div class='empty-state-icon'>
                    <span style='display:inline-block;width:32px;height:32px;
                          background:#16A34A;border-radius:50%;'></span>
                </div>
                <div class='empty-state-title'>Territorio en rango normal</div>
                <div class='empty-state-text'>
                    No hay alertas preventivas activas en este período.<br>
                    Los 103 municipios monitoreados están dentro de los rangos
                    esperados según el modelo XGBoost.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Mostrar alertas en sub-columnas de 2
            for i in range(0, min(len(alertas), 6), 2):
                sub_cols = st.columns(2)
                for j, sub_col in enumerate(sub_cols):
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

                    with sub_col:
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
                                    <div class='pred-label'>Desviación</div>
                                    <div class='pred-value {"pred-delta-pos" if desv > 0 else "pred-delta-neg"}'>
                                        {desv:+.1f}%
                                    </div>
                                </div>
                            </div>
                            <div style='font-size:0.75rem;color:#64748B;margin-bottom:6px;'>
                                Media histórica: {media:.1f} casos/sem
                            </div>
                            <div class='causal-tag'>Causa principal: {var}</div>
                        </div>
                        """, unsafe_allow_html=True)

            if len(alertas) > 6:
                st.caption(f"Mostrando 6 de {len(alertas)} alertas. "
                           "Consulta el historial completo en Datos Abiertos.")

    # ── Columna derecha: Predicción en vivo ────────────────
    with col_prediccion:
        st.markdown(
            "<div class='section-title'>Predicción XGBoost en vivo</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Selecciona un municipio del Valle de Aburrá. "
            "El backend autocompleta las features desde la BD."
        )

        with st.form("prediccion_form"):
            mun_elegido = st.selectbox(
                "Municipio",
                options=list(MUNICIPIOS_VA.keys()),
                format_func=lambda x: f"{MUNICIPIOS_VA[x]} ({x})",
            )
            submit = st.form_submit_button(
                "Ejecutar predicción", use_container_width=True, type="primary"
            )

        if submit:
            with st.spinner("Conectando con XGBoost..."):
                try:
                    payload = {"codigo_dane": mun_elegido, "semana_epi": semana, "anio": anio}
                    r = requests.post(f"{API}/prediccion/", json=payload, timeout=10)
                    result = r.json() if r.status_code == 200 else None
                except Exception:
                    result = None

            if result:
                nivel = result.get("nivel_alerta", "")
                is_roja = "ROJA" in nivel
                is_naranja = "NARANJA" in nivel
                border_color = "#DC2626" if is_roja else "#D97706" if is_naranja else "#16A34A"
                pred = result.get("prediccion_casos_t1", 0)
                desv = result.get("desviacion_pct", 0) or 0
                var = result.get("variable_causal", "N/D")

                st.markdown(f"""
                <div style='background:white; border-left:5px solid {border_color};
                            padding:16px; border-radius:8px;
                            box-shadow:0 2px 4px rgba(0,0,0,0.08);'>
                    <div style='font-size:1rem;font-weight:700;color:#1A2332;
                                margin-bottom:12px;'>
                        Resultado: {MUNICIPIOS_VA[mun_elegido]}
                    </div>
                    <div style='font-size:2.2rem;font-weight:700;color:#1A5F7A;
                                margin-bottom:8px;'>
                        {pred:.1f}
                        <span style='font-size:0.9rem;font-weight:400;color:#64748B;'>
                            casos predichos (t+1)</span>
                    </div>
                    <div class='pred-grid'>
                        <div>
                            <div class='pred-label'>Estado</div>
                            <div style='font-weight:600;color:{border_color};'>
                                {nivel.replace('ALERTA_', '')}</div>
                        </div>
                        <div>
                            <div class='pred-label'>Desviación histórica</div>
                            <div class='pred-value {"pred-delta-pos" if desv > 0 else "pred-delta-neg"}'
                                 style='font-size:1.1rem;'>
                                {desv:+.1f}%</div>
                        </div>
                    </div>
                    <div class='causal-tag' style='margin-top:12px;'>
                        Causa principal (SHAP): {var}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("No se pudo conectar con la API de predicción. "
                         "Verifica que el backend esté activo.")
        else:
            st.markdown("""
            <div style='background:#F7F8FA;border:1px dashed #CBD5E1;
                        border-radius:8px;padding:24px;text-align:center;
                        color:#64748B;font-size:0.85rem;'>
                Selecciona un municipio y ejecuta la predicción para ver
                el resultado del modelo XGBoost con datos reales de la BD.
            </div>
            """, unsafe_allow_html=True)


def render_perfil(anio: int, semana: int):
    st.markdown("""
    <p class='page-title'>Perfil epidemiológico por municipio</p>
    <p class='page-subtitle'>
        Historial de alertas, tendencias y contexto socioeconómico por municipio
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col_select, col_anio = st.columns([2, 1])
    with col_select:
        mun_options = {f"{v} ({k})": k for k, v in MUNICIPIOS_VA.items()}
        mun_sel = st.selectbox(
            "Municipio", options=list(mun_options.keys()), index=0, key="perfil_mun",
        )
        cod = mun_options[mun_sel]
    with col_anio:
        anio_h = st.selectbox(
            "Año", [2023, 2022, 2021, 2020, 2019, 2018], key="perfil_anio"
        )

    if st.button("Consultar perfil", type="primary"):
        with st.spinner("Cargando historial..."):
            hist = _historial(cod.zfill(5), anio_h)

        if hist:
            res = hist.get("resumen_alertas", {})
            n_rojas = res.get("ALERTA_ROJA", 0)
            n_naranjas = res.get("ALERTA_NARANJA", 0)
            n_verdes = res.get("ALERTA_VERDE", 0)
            total_sem = hist.get("total_semanas", 0)

            # KPIs del municipio
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""
                <div class='kpi-card'>
                    <div class='kpi-label'>Semanas registradas</div>
                    <div class='kpi-value' style='color:#1A5F7A;'>{total_sem}</div>
                </div>""", unsafe_allow_html=True)
            with k2:
                st.markdown(f"""
                <div class='kpi-card'>
                    <div class='kpi-label'>Alertas críticas</div>
                    <div class='kpi-value' style='color:#DC2626;'>{n_rojas}</div>
                </div>""", unsafe_allow_html=True)
            with k3:
                st.markdown(f"""
                <div class='kpi-card'>
                    <div class='kpi-label'>Alertas monitoreo</div>
                    <div class='kpi-value' style='color:#D97706;'>{n_naranjas}</div>
                </div>""", unsafe_allow_html=True)
            with k4:
                pct_normal = (n_verdes / total_sem * 100) if total_sem > 0 else 0
                st.markdown(f"""
                <div class='kpi-card'>
                    <div class='kpi-label'>Semanas normales</div>
                    <div class='kpi-value' style='color:#16A34A;'>{pct_normal:.0f}%</div>
                    <div class='kpi-hint'>{n_verdes} de {total_sem} semanas</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # Tabla de historial
            st.markdown(
                "<div class='section-title'>Historial semanal de alertas</div>",
                unsafe_allow_html=True,
            )

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
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                )
        else:
            st.warning(f"No se encontró historial para {mun_sel} en {anio_h}.")