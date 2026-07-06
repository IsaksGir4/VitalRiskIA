"""Transparencia IA — métricas XGBoost + justificaciones.

FIX v3:
- Justificaciones movidas al lado del gráfico (2 columnas)
- Sin espacio en blanco perdido
- Layout compacto
"""
import streamlit as st
import requests
import pandas as pd
import altair as alt
from config import API


@st.cache_data(ttl=600)
def _metricas():
    try:
        r = requests.get(f"{API}/modelo/metricas", timeout=10)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def render():
    st.markdown("""
    <p class='page-title'>Transparencia y Modelo IA</p>
    <p class='page-subtitle'>
        Ficha técnica del algoritmo XGBoost — criterio MinTIC:
        interpretabilidad y rigor técnico
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.spinner("Cargando métricas del modelo..."):
        data = _metricas()

    if not data:
        st.error("No se pudo conectar con la API de métricas.")
        return

    metricas = data.get("metricas_test", {})
    cv = data.get("cv_temporal", {})
    fi = data.get("feature_importance_gain", {})
    split = data.get("split_temporal", {})
    expl = data.get("explicabilidad", {})

    # ── Métricas principales ──────────────────────────────
    st.markdown(
        "<div class='section-title'>Métricas de rendimiento — Test 2022-2023</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, hint in [
        (c1, "RMSE Test", f"{metricas.get('rmse', 'N/D')}",
         "Raíz del error cuadrático medio (casos/mun-semana)"),
        (c2, "MAE Test", f"{metricas.get('mae', 'N/D')}",
         "Error absoluto medio — error promedio de predicción"),
        (c3, "R² Test", f"{metricas.get('r2', 'N/D')}",
         "Varianza explicada (0=nada, 1=perfecto)"),
        (c4, "Mejora vs Naive", f"+{metricas.get('mejora_vs_naive_pct', 'N/D')}%",
         f"Baseline naive RMSE: {metricas.get('rmse_naive_baseline', 'N/D')}"),
    ]:
        with col:
            st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>{label}</div>
                <div class='kpi-value'>{val}</div>
                <div class='kpi-hint'>{hint}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Reemplaza desde donde empieza la Gráfica hasta el final ──
    col_fi, col_info = st.columns([1.2, 1]) # Columnas asimétricas

    with col_fi:
        st.markdown("<div class='section-title'>Importancia de Variables (XGBoost)</div>", unsafe_allow_html=True)
        if fi:
            fi_sorted = sorted(fi.items(), key=lambda x: x[1], reverse=True)
            df_fi = pd.DataFrame(fi_sorted, columns=["feature", "importancia"])

            chart = (
                alt.Chart(df_fi)
                .mark_bar()
                .encode(
                    x=alt.X("importancia:Q", title="Importancia (gain normalizado)",
                             axis=alt.Axis(format=".3f")),
                    y=alt.Y("feature:N", sort="-x", title=None),
                    color=alt.condition(
                        alt.datum.importancia > 0.1,
                        alt.value("#1A5F7A"),
                        alt.value("#93C5FD"),
                    ),
                    tooltip=[
                        alt.Tooltip("feature:N", title="Feature"),
                        alt.Tooltip("importancia:Q", title="Importancia", format=".4f"),
                    ],
                )
                .properties(height=340)
                .configure_axis(labelFontSize=11, grid=True, gridColor="#F0F0F0")
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(chart, width="stretch")
            st.caption(
                "Esta importancia alimenta `variable_causal` en cada alerta. "
                "pm25_avg es la variable causal más frecuente (25.4% de alertas)."
            )
        else:
            st.warning("No se encontró información de feature importance.")
            
    with col_info:
        st.markdown("<div class='section-title'>Justificación de Decisiones Técnicas</div>", unsafe_allow_html=True)
        
        justifs = [
            ("¿Por qué XGBoost y no SARIMAX?",
             "SARIMAX modela una serie temporal univariada. Con 103 municipios "
             "simultáneos y 34 features que incluyen variables ambientales y "
             "socioeconómicas, XGBoost captura interacciones complejas."),
            ("¿Por qué R² negativo en validación?",
             "El validation set es 100% período pandemia (2021). Los casos de "
             "IRA colapsaron por cuarentenas. R²=0.607 en test 2022-2023 es "
             "la métrica relevante para producción."),
            ("¿Por qué RMSE y no AUC-ROC?",
             "El problema es de regresión (predecir conteo de casos), no "
             "clasificación. AUC-ROC es para clasificación binaria."),
            ("Explicabilidad (SHAP)",
             "El modelo usa TreeExplainer. Causa más frecuente: pm25_avg.")
        ]
        
        for titulo, texto in justifs:
            st.markdown(f"""
            <div style='background:#F8F9FA; padding:15px; border-radius:8px; border-left:4px solid #1A5F7A; margin-bottom:10px;'>
                <b style='color:#1A2332; font-size:0.95rem;'>{titulo}</b><br>
                <span style='color:#475569; font-size:0.85rem;'>{texto}</span>
            </div>
            """, unsafe_allow_html=True)

    # ── Configuración + CV Temporal (2 columnas) ──────────
    col_config, col_cv = st.columns([1, 1])

    with col_config:
        st.markdown(
            "<div class='section-title'>Configuración del modelo</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"""
**Algoritmo:** {data.get('algoritmo', 'XGBoost Regressor')}

**Split temporal:**
- Train: {split.get('train', '2018-2020 (498 filas)')}
- Validation: {split.get('validation', '2021 (53 filas — 100% pandemia)')}
- Test: {split.get('test', '2022-2023 (256 filas)')}

**¿Por qué cronológico?** Los datos epidemiológicos tienen autocorrelación
temporal fuerte (lag1 r=0.852). Un split aleatorio causaría data leakage.

**Explicabilidad SHAP:**
- Método: {expl.get('metodo', 'SHAP TreeExplainer')}
- Base value: {expl.get('base_value', '3.2665')} casos
- Variable causal más frecuente: `{expl.get('variable_causal_mas_frecuente', 'pm25_avg')}`
        """)

    with col_cv:
        st.markdown(
            "<div class='section-title'>Validación cruzada temporal</div>",
            unsafe_allow_html=True,
        )
        rmse_folds = cv.get("rmse_por_fold", [])
        if rmse_folds:
            df_cv = pd.DataFrame({
                "Fold": [f"Fold {i+1}" for i in range(len(rmse_folds))],
                "RMSE": rmse_folds,
            })

            chart_cv = (
                alt.Chart(df_cv)
                .mark_bar()
                .encode(
                    x=alt.X("Fold:N", title=None),
                    y=alt.Y("RMSE:Q", title="RMSE"),
                    color=alt.condition(
                        alt.datum.RMSE > 3.0,
                        alt.value("#F59E0B"),
                        alt.value("#1A5F7A"),
                    ),
                    tooltip=["Fold:N", alt.Tooltip("RMSE:Q", format=".4f")],
                )
                .properties(height=200)
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(chart_cv, width="stretch")

            st.markdown(
                f"**Media CV:** {cv.get('rmse_medio', 'N/D')} "
                f"± {cv.get('rmse_std', 'N/D')}"
            )
            st.caption(
                "Alta varianza entre folds es esperada: Fold 1 tiene pocos datos "
                "de entrenamiento, Fold 4 corresponde al período pandemia."
            )
        else:
            st.info("No hay datos de validación cruzada disponibles.")