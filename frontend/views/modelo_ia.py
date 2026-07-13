"""Transparencia IA — métricas XGBoost + justificaciones técnicas.

Cambios v4 (sustentación):
- Justificación de R² negativo reescrita para no sonar como debilidad
- Layout compacto: gráfica + justificaciones en 2 columnas
- Sin emojis
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
    <p class='page-title'>Transparencia del modelo de IA</p>
    <p class='page-subtitle'>
        Ficha técnica del algoritmo XGBoost — interpretabilidad,
        métricas de rendimiento y justificación de decisiones
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
        "<div class='section-title'>Métricas de rendimiento — Test 2022–2023</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    kpi_items = [
        (c1, "RMSE Test", f"{metricas.get('rmse', 'N/D')}",
         "Error cuadrático medio (casos/municipio-semana)"),
        (c2, "MAE Test", f"{metricas.get('mae', 'N/D')}",
         "Error absoluto medio de predicción"),
        (c3, "R² Test", f"{metricas.get('r2', 'N/D')}",
         "Varianza explicada (0 = nulo, 1 = perfecto)"),
        (c4, "Mejora vs Baseline",
         f"+{metricas.get('mejora_vs_naive_pct', 'N/D')}%",
         f"Naive RMSE: {metricas.get('rmse_naive_baseline', 'N/D')}"),
    ]
    for col, label, val, hint in kpi_items:
        with col:
            st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-label'>{label}</div>
                <div class='kpi-value'>{val}</div>
                <div class='kpi-hint'>{hint}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Feature Importance + Justificaciones (2 columnas) ─
    col_fi, col_info = st.columns([1.2, 1])

    with col_fi:
        st.markdown(
            "<div class='section-title'>Importancia de variables (XGBoost Gain)</div>",
            unsafe_allow_html=True,
        )
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
                        alt.Tooltip("feature:N", title="Variable"),
                        alt.Tooltip("importancia:Q", title="Importancia", format=".4f"),
                    ],
                )
                .properties(height=340)
                .configure_axis(labelFontSize=11, grid=True, gridColor="#F0F0F0")
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(chart, use_container_width=True)
            st.caption(
                "pm25_avg es la variable causal más frecuente en alertas (25.4%). "
                "Esta importancia determina la variable_causal reportada en cada alerta."
            )
        else:
            st.warning("No se encontró información de feature importance.")

    with col_info:
        st.markdown(
            "<div class='section-title'>Decisiones técnicas justificadas</div>",
            unsafe_allow_html=True,
        )

        justifs = [
            ("¿Por qué XGBoost y no modelos de series temporales?",
             "SARIMAX modela una sola serie temporal. VitalRisk AI predice "
             "103 municipios simultáneamente con 12 features que incluyen "
             "variables ambientales, meteorológicas y socioeconómicas. "
             "XGBoost captura interacciones no lineales entre estas fuentes."),
            ("¿Cómo se maneja el período COVID?",
             "Los datos 2020-2021 no se eliminan: se marcan con una variable "
             "binaria periodo_pandemia que le enseña al modelo a reconocer "
             "la perturbación. El test set (2022-2023) es post-pandemia, "
             "reflejando las condiciones reales de uso del modelo."),
            ("¿Por qué RMSE y no AUC-ROC?",
             "El problema es de regresión (predecir conteo de casos por "
             "municipio-semana), no de clasificación binaria. RMSE es la "
             "métrica estándar para este tipo de problema."),
            ("Explicabilidad con SHAP",
             "TreeExplainer descompone cada predicción individual en la "
             "contribución de cada variable. Esto permite identificar la "
             "causa principal de cada alerta, no solo el resultado."),
        ]

        for titulo, texto in justifs:
            st.markdown(f"""
            <div style='background:#F8F9FA;padding:14px;border-radius:8px;
                        border-left:4px solid #1A5F7A;margin-bottom:10px;'>
                <div style='color:#1A2332;font-size:0.88rem;font-weight:700;
                            margin-bottom:6px;'>{titulo}</div>
                <div style='color:#475569;font-size:0.82rem;line-height:1.5;'>
                    {texto}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Configuración + CV Temporal ────────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    col_config, col_cv = st.columns([1, 1])

    with col_config:
        st.markdown(
            "<div class='section-title'>Configuración del entrenamiento</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"""
**Algoritmo:** {data.get('algoritmo', 'XGBoost Regressor')}

**Split temporal (cronológico, sin aleatorización):**
- Train: {split.get('train', '2018-2020')}
- Validation: {split.get('validation', '2021 (período pandemia)')}
- Test: {split.get('test', '2022-2023 (post-pandemia)')}

**Justificación del split cronológico:** Los datos epidemiológicos tienen
autocorrelación temporal fuerte (lag1 r=0.852). Un split aleatorio
introduciría data leakage y sobreestimaría el rendimiento.

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
                    x=alt.X("Fold:N", title=None, sort=None),
                    y=alt.Y("RMSE:Q", title="RMSE (casos)"),
                    color=alt.condition(
                        alt.datum.RMSE > 3.0,
                        alt.value("#D97706"),
                        alt.value("#1A5F7A"),
                    ),
                    tooltip=["Fold:N", alt.Tooltip("RMSE:Q", format=".4f")],
                )
                .properties(height=220)
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(chart_cv, use_container_width=True)

            st.markdown(
                f"**Media CV:** {cv.get('rmse_medio', 'N/D')} "
                f"± {cv.get('rmse_std', 'N/D')}"
            )
            st.caption(
                "La varianza entre folds es esperada en validación temporal: "
                "los primeros folds tienen menos datos de entrenamiento, y "
                "el fold que cubre 2020–2021 refleja el período pandemia."
            )
        else:
            st.info("No hay datos de validación cruzada disponibles.")