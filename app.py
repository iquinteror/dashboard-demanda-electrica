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
# CARGA DE DATOS (CON LIMPIEZA Y HOMOLOGACIÓN DE BOGOTÁ)
# ==========================================================
@st.cache_data
def cargar_datos():
    df_depto = pd.read_csv("predicciones_departamentos_2026.csv")
    df_muni_raw = pd.read_csv("predicciones_festivos_2026.csv")
    df_importancia = pd.read_csv("importancia_caracteristicas.csv")
    df_sector_hist = pd.read_csv("analisis_sectorial_historico.csv")

    # Asegurar que las columnas clave no tengan espacios en blanco alrededor
    if "nivel" in df_muni_raw.columns:
        df_muni_raw["nivel"] = df_muni_raw["nivel"].str.strip()
    df_muni_raw["departamento"] = df_muni_raw["departamento"].str.strip()
    df_muni_raw["municipio"] = df_muni_raw["municipio"].str.strip()

    # 🛑 FILTRO INTELIGENTE: Excluir filas agregadas de departamentos, pero rescatar Bogotá municipio
    if "nivel" in df_muni_raw.columns:
        # Mantenemos las filas que sean estrictamente 'municipio'
        df_muni = df_muni_raw[df_muni_raw["nivel"] == "municipio"].copy()
    else:
        # Filtro de seguridad alternativo por si no detecta la columna nivel
        df_muni = df_muni_raw[df_muni_raw["municipio"] != df_muni_raw["departamento"]].copy()
        # Rescate explícito para Bogotá si se usó el filtro alternativo
        filas_bogota = df_muni_raw[df_muni_raw["departamento"] == "Bogotá"].copy()
        df_muni = pd.concat([df_muni, filas_bogota]).drop_duplicates()

    # 🎯 HOMOLOGACIÓN CRÍTICA: Convertir "Bogotá (municipio)" en "Bogotá" para que los filtros unifiquen los datos
    df_muni["municipio"] = df_muni["municipio"].replace({"Bogotá (municipio)": "Bogotá"})
    df_muni["departamento"] = df_muni["departamento"].replace({"Bogotá (municipio)": "Bogotá"})

    # Convertir fechas
    df_depto["fecha"] = pd.to_datetime(df_depto["fecha"])
    df_muni["fecha"] = pd.to_datetime(df_muni["fecha"])
    df_sector_hist["fecha"] = pd.to_datetime(df_sector_hist["fecha"])

    return df_depto, df_muni, df_importancia, df_sector_hist

try:
    df_depto, df_muni, df_importancia, df_sector_hist = cargar_datos()
except:
    st.error("No se encontraron los archivos CSV requeridos en el repositorio o tienen un formato incompatible.")
    st.stop()

# ==========================================================
# TÍTULO PRINCIPAL
# ==========================================================
st.title("⚡ Análisis del Consumo Eléctrico en Días Festivos")
st.markdown("Predicción de demanda para el primer semestre de 2026 y caracterización del comportamiento industrial histórico (2022-2026).")
st.write("---")

# ==========================================================
# FILTRO GLOBAL (Para barras laterales)
# ==========================================================
st.sidebar.header("Filtros")
depto_seleccionado = st.sidebar.selectbox(
    "Seleccione un departamento",
    sorted(df_depto["departamento"].unique())
)

df_depto_filtrado = df_depto[df_depto["departamento"] == depto_seleccionado]
df_muni_filtrado = df_muni[df_muni["departamento"] == depto_seleccionado]

# ==========================================================
# PESTAÑAS (ORDEN LÓGICO)
# ==========================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏢 Vista Departamental",
    "🏙 Vista Municipal",
    "⚙ Modelo Predictivo",
    "🔥 Sectores Económicos",
    "📌 Conclusiones"
])

# ==========================================================
# TAB 1: VISTA DEPARTAMENTAL
# ==========================================================
with tab1:
    st.header(f"Análisis Departamental: {depto_seleccionado}")
    
    col1, col2, col3 = st.columns(3)
    
    consumo_real = df_depto_filtrado["demanda_departamental_real_gwh"].sum()
    consumo_predicho = df_depto_filtrado["demanda_departamental_predicha_gwh"].sum()
    lluvia_promedio = df_depto_filtrado["lluvia_promedio_depto_mm"].mean()

    col1.metric("Consumo Real", f"{consumo_real:.2f} GWh")
    col2.metric("Consumo Predicho", f"{consumo_predicho:.2f} GWh")
    col3.metric("Precipitación Promedio", f"{lluvia_promedio:.2f} mm")

    st.write("---")
    st.subheader("Predicción vs Realidad")
    
    if len(df_depto_filtrado) > 0:
        df_melted = df_depto_filtrado.melt(
            id_vars="fecha",
            value_vars=["demanda_departamental_real_gwh", "demanda_departamental_predicha_gwh"],
            var_name="Tipo", value_name="Consumo"
        )
        df_melted["Tipo"] = df_melted["Tipo"].replace({
            "demanda_departamental_real_gwh": "Real",
            "demanda_departamental_predicha_gwh": "Predicho"
        })

        fig_lineas = px.line(df_melted, x="fecha", y="Consumo", color="Tipo", markers=True, title="Curvas de demanda")
        st.plotly_chart(fig_lineas, use_container_width=True)

        st.subheader("Relación entre lluvia y consumo")
        fig_lluvia = px.scatter(df_depto_filtrado, x="lluvia_promedio_depto_mm", y="demanda_departamental_real_gwh", hover_data=["fecha"], trendline="ols")
        st.plotly_chart(fig_lluvia, use_container_width=True)
    else:
        st.warning("No se encontraron registros de curvas para la selección actual.")

# ==========================================================
# TAB 2: VISTA MUNICIPAL
# ==========================================================
with tab2:
    st.header(f"Municipios del departamento {depto_seleccionado}")
    
    if len(df_muni_filtrado) > 0:
        st.subheader("Municipios con mayor consumo (Top 10)")
        top_munis = df_muni_filtrado.groupby("municipio")["demanda_municipio_est_gwh"].sum().reset_index().sort_values(by="demanda_municipio_est_gwh", ascending=False).head(10)
        
        fig_bar = px.bar(
            top_munis, x="demanda_municipio_est_gwh", y="municipio", orientation="h",
            title="Top 10 Municipios con Mayor Demanda Energética Real en Festivos",
            labels={'demanda_municipio_est_gwh': 'Consumo Acumulado (GWh)', 'municipio': 'Municipio'}
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Municipios con mayor error promedio")
        col_error = "error_absolute" if "error_absolute" in df_muni_filtrado.columns else "error_absoluto"
        top_error = df_muni_filtrado.groupby("municipio")[col_error].mean().reset_index().sort_values(by=col_error, ascending=False).head(10)
        
        fig_error = px.bar(
            top_error, x=col_error, y="municipio", orientation="h",
            title="Top 10 Municipios con Mayor Desviación del Modelo",
            labels={col_error: 'Error Absoluto Promedio (GWh)', 'municipio': 'Municipio'}
        )
        fig_error.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_error, use_container_width=True)
    else:
        st.info("No hay desglose de sub-municipios disponible para esta entidad territorial.")

# ==========================================================
# TAB 3: MODELO PREDICTIVO
# ==========================================================
with tab3:
    st.header("Modelo Random Forest")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("R²", "0.9302")
        st.metric("MAPE", "16.82%")
        st.metric("MAE", "0.0267 GWh")
        st.metric("RMSE", "0.1795 GWh")

    with col2:
        st.markdown("""
        ### Metodología
        - Entrenamiento: 2022-2025.
        - Datos diarios completos.
        - Test: Festivos enero-mayo 2026.
        - Algoritmo: Random Forest Regressor.
        """)

    st.write("---")
    st.subheader("Importancia de características")
    fig_imp = px.bar(df_importancia, x="Importancia", y="Caracteristica", orientation="h")
    fig_imp.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_imp, use_container_width=True)

    st.subheader("Real vs Predicho")
    fig_real_pred = px.scatter(df_muni, x="demanda_municipio_est_gwh", y="demanda_predicha_gwh", opacity=0.6)
    st.plotly_chart(fig_real_pred, use_container_width=True)

# ==========================================================
# TAB 4: 🔥 SECTORES ECONÓMICOS
# ==========================================================
with tab4:
    st.header("🔥 Estructura del Consumo Eléctrico Nacional (2022-2026)")
    st.markdown("""
    Esta pestaña presenta la radiografía completa del consumo eléctrico sectorial acumulado desde 2022 hasta el 2026. 
    Permite identificar qué industrias sostienen la demanda energética base del país en los departamentos de manera estructural.
    """)
    
    columnas_industrias = [col for col in df_sector_hist.columns if col not in ['fecha', 'departamento']]
    
    st.subheader("1. Mapa de Calor Histórico: Departamentos × Sectores Económicos")
    
    df_heat_hist = df_sector_hist.groupby('departamento')[columnas_industrias].sum().reset_index()
    df_heat_melted_hist = df_heat_hist.melt(id_vars='departamento', var_name='Sector Industrial', value_name='Consumo_Acumulado_GWh')
    
    fig_heatmap_hist = px.density_heatmap(
        df_heat_melted_hist, x="Sector Industrial", y="departamento", z="Consumo_Acumulado_GWh",
        histfunc="sum", color_continuous_scale="Viridis",
        title="Matriz de Demanda Energética Acumulada por Actividad Comercial y de Manufactura",
        labels={
            'Consumo_Acumulado_GWh': 'Consumo Total (GWh)',
            'Sector Industrial': 'Sector Económico',
            'departamento': 'Departamento'
        }
    )
    st.plotly_chart(fig_heatmap_hist, use_container_width=True)
    
    st.write("---")
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("2. Distribución Nacional por Industria")
        sector_seleccionado = st.selectbox("Seleccione un Sector Industrial para auditar el histórico:", columnas_industrias)
        
        df_ranking_hist = df_heat_hist[['departamento', sector_seleccionado]].sort_values(by=sector_seleccionado, ascending=False).head(10)
        
        fig_ranking_hist_bar = px.bar(
            df_ranking_hist, x=sector_seleccionado, y='departamento', orientation='h',
            title=f"Top 10 Departamentos Líderes en Consumo de: {sector_seleccionado}",
            labels={sector_seleccionado: 'Consumo Acumulado (GWh)', 'departamento': 'Departamento'}
        )
        fig_ranking_hist_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_ranking_hist_bar, use_container_width=True)
        
    with col_der:
        st.subheader("3. Sector Predominante en la Matriz Energética Regional")
        st.markdown("Actividad económica principal que más energía consume históricamente por región:")
        
        df_heat_hist['Sector Predominante'] = df_heat_hist[columnas_industrias].idxmax(axis=1)
        df_heat_hist['Consumo Total Sector (GWh)'] = df_heat_hist[columnas_industrias].max(axis=1)
        
        tabla_dominante_hist = df_heat_hist[['departamento', 'Sector Predominante', 'Consumo Total Sector (GWh)']].sort_values(by='Consumo Total Sector (GWh)', ascending=False)
        tabla_dominante_hist.columns = ['Departamento', 'Sector Predominante (2022-2026)', 'Consumo Histórico (GWh)']
        
        st.dataframe(tabla_dominante_hist, use_container_width=True, hide_index=True)

# ==========================================================
# TAB 5: 📌 CONCLUSIONES
# ==========================================================
with tab5:
    st.header("Conclusiones")
    st.markdown("""
    ### Principales resultados
    - Se entrenó un modelo Random Forest con información diaria comprendida entre 2022 y 2025.
    - El modelo fue evaluado utilizando exclusivamente los días festivos del primer semestre de 2026.
    - Se obtuvo un coeficiente de determinación R² = 0.9302.
    - El algoritmo logró explicar aproximadamente el 93 % de la variabilidad de la demanda eléctrica.
    - Las variables más importantes fueron el municipio y el departamento.
    - La precipitación presentó una influencia reducida sobre el consumo eléctrico.
    - Los patrones sectoriales históricos (2022-2026) demuestran que la infraestructura pesada regional mantiene un consumo rígido que guía la predictibilidad del modelo.
    """)
    st.success("Proyecto de Analítica de Datos Completado con Éxito.")
