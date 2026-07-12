import streamlit as st
from pathlib import Path
from config import API
import requests

st.cache_data.clear()

st.set_page_config(
    page_title="VitalRisk AI — Vigilancia Preventiva Antioquia",
    page_icon="🫁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS
css_path = Path(__file__).parent / "assets" / "custom.css"
if css_path.exists():
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# --- Lógica de Monitoreo Constante (Estado Global) ---
# Estado global — inicializar con la última fecha disponible
@st.cache_data(ttl=60)
def fetch_latest_date():
    try:
        r = requests.get(f"{API}/mapa/ultima_fecha", timeout=5)
        return r.json() if r.status_code == 200 else {"anio": 2026, "semana_epi": 27}
    except Exception:
        return {"anio": 2026, "semana_epi": 27}

latest = fetch_latest_date()

if "anio" not in st.session_state:
    st.session_state.anio = latest.get("anio", 2026)
if "semana" not in st.session_state:
    st.session_state.semana = latest.get("semana_epi", 27)


# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 12px 4px 8px 4px;'>
        <div style='display:flex; align-items:center; gap:10px;'>
            <div style='width:34px;height:34px;background:#1A5F7A;border-radius:8px;
                        display:flex;align-items:center;justify-content:center;'>
                <span style='color:white;font-size:16px;font-weight:700;'>+</span>
            </div>
            <div>
                <div style='font-size:0.9rem;font-weight:700;color:#1A2332;
                            line-height:1.2;'>VitalRisk AI</div>
                <div style='font-size:0.68rem;color:#64748B;'>
                    Vigilancia preventiva · Antioquia</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    vista = st.radio(
        "Navegación",
        [
            "Dashboard territorial",
            "Alertas preventivas",
            "Perfil municipio",
            "Datos abiertos",
            "Transparencia IA",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    
    # Botón para regresar al "En Vivo" rápidamente
    if st.button("🔴 Volver a Monitoreo en Vivo", use_container_width=True):
        st.session_state.anio = latest["anio"]
        st.session_state.semana = latest["semana_epi"]
        st.rerun()

    st.session_state.anio = st.selectbox(
        "Año epidemiológico",
        options=[2026, 2023, 2022, 2021, 2020, 2019, 2018],
        index=[2026, 2023, 2022, 2021, 2020, 2019, 2018].index(st.session_state.anio),
    )

    # Limitar las semanas dinámicamente si es el año actual
    max_sem = latest["semana_epi"] if st.session_state.anio == latest["anio"] else 52
    
    st.session_state.semana = st.selectbox(
        "Semana epidemiológica",
        options=list(range(1, max_sem + 1)),
        index=st.session_state.semana - 1 if st.session_state.semana <= max_sem else 0,
        format_func=lambda x: f"Semana {x:02d}",
        help="Semana del año según calendario INS Colombia",
    )

    st.divider()

    st.caption("Modelo **XGBoost** · RMSE test: **1.74** casos · Entrenado: 2018-2021")

# ── Enrutador ──────────────────────────────────────────────
anio = st.session_state.anio
semana = st.session_state.semana

if "Dashboard" in vista:
    from views.dashboard import render
    render(anio, semana)
elif "Alertas" in vista:
    from views.alertas import render
    render(anio, semana)
elif "Perfil" in vista:
    from views.alertas import render_perfil
    render_perfil(anio, semana)
elif "Datos" in vista:
    from views.opendata import render
    render()
elif "Transparencia" in vista:
    from views.modelo_ia import render
    render()