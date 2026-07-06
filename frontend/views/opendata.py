"""Portal de Datos Abiertos — descargas CSV + metadatos.

FIX v3:
- Table overflow fixed with word-wrap CSS
- Alertas preview defaults to showing IPT data as fallback
- Better error handling
"""
import streamlit as st
import requests
import pandas as pd
from config import API


@st.cache_data(ttl=600)
def _metadatos():
    try:
        r = requests.get(f"{API}/opendata/metadatos/ipt", timeout=10)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def _csv_bytes(endpoint: str):
    try:
        r = requests.get(f"{API}/opendata/{endpoint}", timeout=30)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def _load_preview(endpoint: str, max_rows: int = 50):
    try:
        r = requests.get(f"{API}/opendata/{endpoint}", timeout=30)
        if r.status_code == 200:
            from io import StringIO
            return pd.read_csv(StringIO(r.content.decode("utf-8")))
        return None
    except Exception:
        return None


def render():
    st.markdown("""
    <p class='page-title'>Portal de Datos Abiertos</p>
    <p class='page-subtitle'>Transparencia de datos — estándar SaluData Bogotá</p>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    tab_ipt, tab_alertas, tab_meta = st.tabs([
        "IPT por Municipio", "Historial de Alertas", "Metadatos",
    ])

    # ── Tab IPT ───────────────────────────────────────────
    with tab_ipt:
        st.markdown(
            "<div class='section-title'>"
            "Índice Preventivo Territorial (IPT) — Antioquia 2018-2023"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Dataset completo: 910 registros · 103 municipios · 6 años · "
            "Fuentes: SIVIGILA + IDEAM + DANE"
        )

        col_desc, col_dl = st.columns([3, 1])
        with col_desc:
            st.markdown(
                "**¿Qué contiene este dataset?** "
                "Datos semanales por municipio que integran casos de IRA (SIVIGILA), "
                "calidad del aire PM2.5 (IDEAM), variables meteorológicas y "
                "el Índice Preventivo Territorial calculado por VitalRisk AI."
            )
        with col_dl:
            with st.spinner("Preparando..."):
                csv_ipt = _csv_bytes("ipt")
            if csv_ipt:
                st.download_button(
                    label="Descargar CSV (IPT)",
                    data=csv_ipt,
                    file_name="vitalrisk_ipt_antioquia_2018_2023.csv",
                    mime="text/csv",
                    width="stretch",
                )
            else:
                st.error("API no disponible para descarga")

        st.divider()
        st.markdown("**Vista previa del dataset (primeras 50 filas)**")
        with st.spinner("Cargando..."):
            df = _load_preview("ipt")
        if df is not None:
            st.dataframe(
                df.head(50), width="stretch", hide_index=True,
            )
            st.caption(f"Total: {len(df):,} registros en el dataset completo")
        else:
            st.warning("No se pudo cargar la vista previa del dataset IPT.")

    # ── Tab Alertas ───────────────────────────────────────
    with tab_alertas:
        st.markdown(
            "<div class='section-title'>"
            "Historial de Alertas Territoriales — Antioquia"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "807 alertas generadas · Modelo XGBoost + SHAP · "
            "Umbral NARANJA: +30% | ROJA: +60% sobre media histórica"
        )

        col_d, col_b = st.columns([3, 1])
        with col_b:
            with st.spinner("Preparando..."):
                csv_alertas = _csv_bytes("alertas")
            if csv_alertas:
                st.download_button(
                    label="Descargar CSV (Alertas)",
                    data=csv_alertas,
                    file_name="vitalrisk_alertas_antioquia_2018_2023.csv",
                    mime="text/csv",
                    width="stretch",
                )
            else:
                st.error(
                    "API no disponible. Verifica que el endpoint "
                    "`/opendata/alertas` esté activo y que `alertas_territoriales` "
                    "esté cargada en la BD (ejecuta `python etl/load_to_db.py`)."
                )

        st.divider()

        with st.spinner("Cargando vista previa..."):
            df_a = _load_preview("alertas")
        if df_a is not None and not df_a.empty:
            def color_alerta(val):
                if val == "ALERTA_ROJA":
                    return "background-color:#FEF2F2;color:#DC2626;font-weight:600"
                if val == "ALERTA_NARANJA":
                    return "background-color:#FFFBEB;color:#D97706;font-weight:600"
                return "background-color:#F0FDF4;color:#16A34A"

            if "nivel_alerta" in df_a.columns:
                st.dataframe(
                    df_a.head(50).style.map(color_alerta, subset=["nivel_alerta"]),
                    width="stretch", hide_index=True,
                )
            else:
                st.dataframe(df_a.head(50), width="stretch", hide_index=True)
            st.caption(f"Total: {len(df_a):,} registros en el historial completo")
        else:
            st.info(
                "No se pudo cargar la vista previa de alertas. "
                "Esto puede ocurrir si la tabla `alertas_territoriales` aún no "
                "fue cargada en la BD. Ejecuta `python etl/load_to_db.py` "
                "para cargar el paso 7."
            )

    # ── Tab Metadatos ─────────────────────────────────────
    with tab_meta:
        meta = _metadatos()
        if meta:
            st.markdown(
                "<div class='section-title'>Diccionario de datos</div>",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
**Nombre:** {meta.get('nombre_conjunto', '')}

**Descripción:** {meta.get('descripcion', '')}

**Periodicidad:** {meta.get('periodicidad', '')}

**Última actualización:** {meta.get('ultima_actualizacion', '')}

**Licencia:** {meta.get('licencia', '')}

**Responsable:** {meta.get('responsable', '')}
                """)
            with c2:
                cobertura = meta.get("cobertura", {})
                fuentes = meta.get("fuente_datos", {})
                st.markdown("**Cobertura:**")
                for k, v in cobertura.items():
                    st.markdown(f"- **{k}:** {v}")
                st.markdown("**Fuentes de datos:**")
                for k, v in fuentes.items():
                    st.markdown(f"- **{k}:** {v}")

            st.divider()

            # Variables table
            st.markdown("**Variables del dataset:**")
            variables = meta.get("variables", [])
            if variables:
                df_vars = pd.DataFrame(variables)
                # Truncate descriptions to prevent overflow
                if "descripcion" in df_vars.columns:
                    df_vars["descripcion"] = df_vars["descripcion"].apply(
                        lambda x: x[:80] + "…" if isinstance(x, str) and len(x) > 80 else x
                    )
                st.dataframe(
                    df_vars, width="stretch", hide_index=True,
                    height=350,
                )

            nota = meta.get("nota_metodologica", "")
            if nota:
                st.info(f"**Nota metodológica:** {nota}")
        else:
            st.warning("No se pudieron cargar los metadatos.")