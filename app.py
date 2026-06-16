import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================================
st.set_page_config(
    page_title="Dashboard de Demanda Eléctrica",
    layout="wide"
)

# ==========================================================
# CARGA DE DATOS
# ==========================================================
@st.cache_data
def cargar_datos():

    df_depto = pd.read_csv(
        "predicciones_departamentos_2026.csv"
    )

    df_muni = pd.read_csv(
        "predicciones_festivos_2026.csv"
    )

    df_importancia = pd.read_csv(
        "importancia_caracteristicas.csv"
    )

    df_depto["fecha"] = pd.to_datetime(df_depto["fecha"])
    df_muni["fecha"] = pd.to_datetime(df_muni["fecha"])

    return df_depto, df_muni, df_importancia


try:

    df_depto, df_muni, df_importancia = cargar_datos()

except:

    st.error(
        "No se encontraron los archivos CSV."
    )

    st.stop()

# ==========================================================
# TÍTULO
# ==========================================================
st.title("⚡ Análisis del Consumo Eléctrico en Días Festivos")

st.markdown(
"""
Predicción de la demanda eléctrica en Colombia y análisis
del impacto de la precipitación para el primer semestre de 2026.
"""
)

st.write("---")

# ==========================================================
# FILTRO GLOBAL
# ==========================================================
st.sidebar.header("Filtros")

depto_seleccionado = st.sidebar.selectbox(
    "Seleccione un departamento",
    sorted(df_depto["departamento"].unique())
)

df_depto_filtrado = df_depto[
    df_depto["departamento"] == depto_seleccionado
]

df_muni_filtrado = df_muni[
    df_muni["departamento"] == depto_seleccionado
]

# ==========================================================
# PESTAÑAS
# ==========================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🏢 Vista Departamental",
    "🏙 Vista Municipal",
    "⚙ Modelo Predictivo",
    "📌 Conclusiones"
])

# ==========================================================
# TAB 1
# ==========================================================
with tab1:

    st.header(f"Análisis Departamental: {depto_seleccionado}")

    col1, col2, col3 = st.columns(3)

    consumo_real = (
        df_depto_filtrado[
            "demanda_departamental_real_gwh"
        ].sum()
    )

    consumo_predicho = (
        df_depto_filtrado[
            "demanda_departamental_predicha_gwh"
        ].sum()
    )

    lluvia_promedio = (
        df_depto_filtrado[
            "lluvia_promedio_depto_mm"
        ].mean()
    )

    col1.metric(
        "Consumo Real",
        f"{consumo_real:.2f} GWh"
    )

    col2.metric(
        "Consumo Predicho",
        f"{consumo_predicho:.2f} GWh"
    )

    col3.metric(
        "Precipitación Promedio",
        f"{lluvia_promedio:.2f} mm"
    )

    st.write("---")

    st.subheader(
        "Predicción vs Realidad"
    )

    df_melted = df_depto_filtrado.melt(
        id_vars="fecha",
        value_vars=[
            "demanda_departamental_real_gwh",
            "demanda_departamental_predicha_gwh"
        ],
        var_name="Tipo",
        value_name="Consumo"
    )

    df_melted["Tipo"] = df_melted["Tipo"].replace({
        "demanda_departamental_real_gwh": "Real",
        "demanda_departamental_predicha_gwh": "Predicho"
    })

    fig_lineas = px.line(
        df_melted,
        x="fecha",
        y="Consumo",
        color="Tipo",
        markers=True,
        title="Curvas de demanda"
    )

    st.plotly_chart(
        fig_lineas,
        use_container_width=True
    )

    st.subheader(
        "Relación entre lluvia y consumo"
    )

    fig_lluvia = px.scatter(
        df_depto_filtrado,
        x="lluvia_promedio_depto_mm",
        y="demanda_departamental_real_gwh",
        hover_data=["fecha"],
        trendline="ols"
    )

    st.plotly_chart(
        fig_lluvia,
        use_container_width=True
    )

# ==========================================================
# TAB 2
# ==========================================================
with tab2:

    st.header(
        f"Municipios del departamento {depto_seleccionado}"
    )

    st.subheader(
        "Municipios con mayor consumo"
    )

    top_munis = (
        df_muni_filtrado
        .groupby("municipio")[
            "demanda_municipio_est_gwh"
        ]
        .sum()
        .reset_index()
        .sort_values(
            by="demanda_municipio_est_gwh",
            ascending=False
        )
    )

    fig_bar = px.bar(
        top_munis,
        x="demanda_municipio_est_gwh",
        y="municipio",
        orientation="h"
    )

    st.plotly_chart(
        fig_bar,
        use_container_width=True
    )

    st.subheader(
        "Municipios con mayor error promedio"
    )

    top_error = (
        df_muni_filtrado
        .groupby("municipio")["error_absoluto"]
        .mean()
        .reset_index()
        .sort_values(
            by="error_absoluto",
            ascending=False
        )
        .head(10)
    )

    fig_error = px.bar(
        top_error,
        x="error_absoluto",
        y="municipio",
        orientation="h"
    )

    st.plotly_chart(
        fig_error,
        use_container_width=True
    )

# ==========================================================
# TAB 3
# ==========================================================
with tab3:

    st.header(
        "Modelo Random Forest"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "R²",
            "0.9302"
        )

        st.metric(
            "MAPE",
            "16.82%"
        )

        st.metric(
            "MAE",
            "0.0267 GWh"
        )

        st.metric(
            "RMSE",
            "0.1795 GWh"
        )

    with col2:

        st.markdown(
        """
### Metodología

- Entrenamiento: 2022-2025.
- Datos diarios completos.
- Test: Festivos enero-mayo 2026.
- Algoritmo: Random Forest Regressor.
"""
        )

    st.write("---")

    st.subheader(
        "Importancia de características"
    )

    fig_imp = px.bar(
        df_importancia,
        x="Importancia",
        y="Caracteristica",
        orientation="h"
    )

    fig_imp.update_layout(
        yaxis={'categoryorder':'total ascending'}
    )

    st.plotly_chart(
        fig_imp,
        use_container_width=True
    )

    st.subheader(
        "Real vs Predicho"
    )

    fig_real_pred = px.scatter(
        df_muni,
        x="demanda_municipio_est_gwh",
        y="demanda_predicha_gwh",
        opacity=0.6
    )

    st.plotly_chart(
        fig_real_pred,
        use_container_width=True
    )

# ==========================================================
# TAB 4
# ==========================================================
with tab4:

    st.header("Conclusiones")

    st.markdown(
"""
### Principales resultados

- Se entrenó un modelo Random Forest con información diaria comprendida entre 2022 y 2025.

- El modelo fue evaluado utilizando exclusivamente los días festivos del primer semestre de 2026.

- Se obtuvo un coeficiente de determinación R² = 0.9302.

- El algoritmo logró explicar aproximadamente el 93 % de la variabilidad de la demanda eléctrica.

- Las variables más importantes fueron el municipio y el departamento.

- La precipitación presentó una influencia reducida sobre el consumo eléctrico.

- Las predicciones obtenidas reprodujeron adecuadamente el comportamiento real de la demanda.

- Los resultados muestran que la localización geográfica tiene mayor impacto que las variables meteorológicas durante los días festivos.
"""
    )

    st.success(
        "Proyecto de Analítica de Datos: Predicción de Demanda Eléctrica en Días Festivos."
    )