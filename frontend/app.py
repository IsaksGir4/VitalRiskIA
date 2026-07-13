import streamlit as st
from pathlib import Path
from datetime import date
from config import API
import requests

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


# --- Estado Global: última fecha disponible ---
def _semana_epi_actual():
    """Fallback dinámico: calcula año y semana epidemiológica actual."""
    hoy = date.today()
    iso_year, iso_week, _ = hoy.isocalendar()
    return {"anio": iso_year, "semana_epi": iso_week}

@st.cache_data(ttl=60)
def fetch_latest_date():
    """Consulta la API por la última semana con datos.
    Si la API no responde, usa la semana epidemiológica de hoy."""
    try:
        r = requests.get(f"{API}/mapa/ultima_fecha", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return _semana_epi_actual()

latest = fetch_latest_date()

if "anio" not in st.session_state:
    st.session_state.anio = latest.get("anio", 2026)
if "semana" not in st.session_state:
    st.session_state.semana = latest.get("semana_epi", 27)


# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    # Logo VitalRisk AI — pulmones SVG inline (no depende de archivos externos)
    st.markdown("""
    <div style='padding: 16px 8px 12px 8px;'>
        <div style='display:flex; align-items:center; gap:12px;'>
            <svg width="38" height="38" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="64" height="64" rx="12" fill="#1A5F7A"/>
                <path d="M32 16C32 16 28 20 28 28C28 32 26 36 22 38C18 40 16 44 16 48C16 48 20 48 24 46C28 44 30 40 30 36L30 28"
                      stroke="white" stroke-width="2.5" stroke-linecap="round" fill="none"/>
                <path d="M32 16C32 16 36 20 36 28C36 32 38 36 42 38C46 40 48 44 48 48C48 48 44 48 40 46C36 44 34 40 34 36L34 28"
                      stroke="white" stroke-width="2.5" stroke-linecap="round" fill="none"/>
                <circle cx="32" cy="14" r="2" fill="#22C55E"/>
            </svg>
            <div>
                <div style='font-size:1rem;font-weight:700;color:#1A2332;
                            line-height:1.2;'>VitalRisk AI</div>
                <div style='font-size:0.7rem;color:#64748B;line-height:1.3;'>
                    Vigilancia preventiva territorial<br>Antioquia · Equipo 326</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    vista = st.radio(
        "Navegación",
        [
            "Dashboard territorial",
            "Alertas y predicción",
            "Perfil municipio",
            "Datos abiertos",
            "Transparencia IA",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # Botón para regresar al período más reciente
    if st.button("Volver al período más reciente", use_container_width=True, type="secondary"):
        st.session_state.anio = latest["anio"]
        st.session_state.semana = latest["semana_epi"]
        st.rerun()

    st.session_state.anio = st.selectbox(
        "Año epidemiológico",
        options=[2026, 2023, 2022, 2021, 2020, 2019, 2018],
        index=[2026, 2023, 2022, 2021, 2020, 2019, 2018].index(st.session_state.anio)
              if st.session_state.anio in [2026, 2023, 2022, 2021, 2020, 2019, 2018] else 0,
    )

    # Limitar las semanas dinámicamente si es el año actual
    max_sem = latest["semana_epi"] if st.session_state.anio == latest["anio"] else 52

    st.session_state.semana = st.selectbox(
        "Semana epidemiológica",
        options=list(range(1, max_sem + 1)),
        index=st.session_state.semana - 1 if st.session_state.semana <= max_sem else 0,
        format_func=lambda x: f"Semana {x:02d}",
        help="Semana del año según calendario epidemiológico del INS",
    )

    st.divider()

    # Info del modelo — tarjeta profesional
    st.markdown("""
    <div style='background:#F7F8FA;border-radius:8px;padding:10px 12px;
                border:1px solid #E2E8F0;font-size:0.75rem;color:#64748B;'>
        <div style='font-weight:600;color:#1A2332;margin-bottom:4px;'>
            Modelo XGBoost v1.0</div>
        RMSE test: <strong style='color:#1A5F7A;'>1.74</strong> casos ·
        R²: <strong style='color:#1A5F7A;'>0.607</strong><br>
        Entrenado: 2018–2021 · Test: 2022–2023
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.caption("Concurso Datos al Ecosistema 2026 · MinTIC")


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