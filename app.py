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
# CARGA Y PREPROCESAMIENTO DE DATOS
# ==========================================================
@st.cache_data
def cargar_datos():
    # Leer archivos directamente
    df_depto = pd.read_csv("predicciones_departamentos_2026.csv")
    df_muni_raw = pd.read_csv("predicciones_festivos_2026.csv")
    df_importancia = pd.read_csv("importancia_caracteristicas.csv")
    df_sector_hist = pd.read_csv("analisis_sectorial_historico.csv")

    # Limpiar espacios invisibles
    df_depto["departamento"] = df_depto["departamento"].astype(str).str.strip()
    df_muni_raw["departamento"] = df_muni_raw["departamento"].astype(str).str.strip()
    df_muni_raw["municipio"] = df_muni_raw["municipio"].astype(str).str.strip()

    # Estandarizar formatos de fecha
    df_depto["fecha"] = pd.to_datetime(df_depto["fecha"])
    df_muni_raw["fecha"] = pd.to_datetime(df_muni_raw["fecha"])
    df_sector_hist["fecha"] = pd.to_datetime(df_sector_hist["fecha"])

    # Separar municipios reales excluyendo filas duplicadas de agregación de control
    # Nota: Dejamos "Bogotá (municipio)" intacto aquí para procesarlo después
    df_muni = df_muni_raw[df_muni_raw["municipio"] != df_muni_raw["departamento"]].copy()
    
    # Agregar explícitamente a Bogotá (municipio) que se excluyó en la regla anterior
    bogota_muni_row = df_muni_raw[(df_muni_raw["departamento"] == "Bogotá") & (df_muni_raw["municipio"] == "Bogotá (municipio)")].copy()
    df_muni = pd.concat([df_muni, bogota_muni_row]).drop_duplicates()

    return df_depto, df_muni, df_muni_raw, df_importancia, df_sector_hist

try:
    df_depto, df_muni, df_muni_raw, df_importancia, df_sector_hist = cargar_datos()
except Exception as e:
    st.error(f"Error al cargar los archivos CSV: {e}")
    st.stop()

# ==========================================================
# FILTRO GLOBAL (Barra Lateral)
# ==========================================================
st.sidebar.header("Filtros")
listado_deptos = sorted(df_depto["departamento"].unique())
depto_seleccionado = st.sidebar.selectbox("Seleccione un departamento", listado_deptos)

# ==========================================================
# PROCESAMIENTO DINÁMICO E INYECCIÓN DE DATOS PARA BOGOTÁ
# ==========================================================
# Si es Bogotá, extraemos sus curvas reales desde el desglose municipal para parchar el vacío de deptos
if depto_seleccionado == "Bogotá":
    # Filtrar la fila municipal real de Bogotá
    df_bogota_real = df_muni_raw[(df_muni_raw["departamento"] == "Bogotá") & (df_muni_raw["municipio"] == "Bogotá (municipio)")].copy()
    
    # Construir un dataframe equivalente estructuralmente al departamental
    df_depto_filtrado = pd.DataFrame({
        "fecha": df_bogota_real["fecha"],
        "departamento": "Bogotá",
        "demanda_departamental_real_gwh": df_bogota_real["demanda_municipio_est_gwh"],
        "demanda_departamental_predicha_gwh": df_bogota_real["demanda_predicha_gwh"],
        # Recuperamos la lluvia que sí venía en el archivo de departamentos
        "lluvia_promedio_depto_mm": df_depto[df_depto["departamento"] == "Bogotá"]["lluvia_promedio_depto_mm"].values
    })
    
    # Para la pestaña municipal, homologamos el nombre para el gráfico de barras
    df_muni_filtrado = df_bogota_real.copy()
    df_muni_filtrado["municipio"] = "Bogotá D.C."
else:
    # Comportamiento estándar para el resto de departamentos colombianos
    df_depto_filtrado = df_depto[df_depto["departamento"] == depto_seleccionado]
    df_muni_filtrado = df_muni[df_muni["departamento"] == depto_seleccionado]

# ==========================================================
# INTERFAZ GRÁFICA: TÍTULOS Y PESTAÑAS
# ==========================================================
st.title("⚡ Análisis del Consumo Eléctrico en Días Festivos")
st.markdown("Predicción de demanda para el primer semestre de 2026 y caracterización estructural del consumo industrial histórico.")
st.write("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏢 Vista Departamental",
    "🏙 Vista Municipal",
    "⚙ Modelo Predictivo",
    "🔥 Sectores Económicos",
    "📌 Conclusiones"
])

# ==========================================================
# TAB 1: VISTA DEPARTAMENTAL (RECONSTRUIDA)
# ==========================================================
with tab1:
    st.header(f"Análisis Departamental: {depto_seleccionado}")
    
    col1, col2, col3 = st.columns(3)
    
    consumo_real = df_depto_filtrado["demanda_departamental_real_gwh"].sum()
    consumo_predicho = df_depto_filtrado["demanda_departamental_predicha_gwh"].sum()
    lluvia_promedio = df_depto_filtrado["lluvia_promedio_depto_mm"].mean()

    col1.metric("Consumo Real Total", f"{consumo_real:.2f} GWh")
    col2.metric("Consumo Predicho Total", f"{consumo_predicho:.2f} GWh")
    col3.metric("Precipitación Promedio", f"{lluvia_promedio:.2f} mm")

    st.write("---")
    st.subheader("Predicción vs Realidad (Curvas de Demanda)")
    
    if len(df_depto_filtrado) > 0 and consumo_real > 0:
        df_melted = df_depto_filtrado.melt(
            id_vars="fecha",
            value_vars=["demanda_departamental_real_gwh", "demanda_departamental_predicha_gwh"],
            var_name="Tipo", value_name="Consumo"
        )
        df_melted["Tipo"] = df_melted["Tipo"].replace({
            "demanda_departamental_real_gwh": "Real",
            "demanda_departamental_predicha_gwh": "Predicho"
        })

        fig_lineas = px.line(df_melted, x="fecha", y="Consumo", color="Tipo", markers=True,
                             title="Evolución del Consumo Energético en Días Festivos (2026)")
        st.plotly_chart(fig_lineas, use_container_width=True)

        st.subheader("Relación entre lluvia y consumo de energía")
        fig_lluvia = px.scatter(df_depto_filtrado, x="lluvia_promedio_depto_mm", y="demanda_departamental_real_gwh", 
                                hover_data=["fecha"], trendline="ols", title="Dispersión: Precipitación vs Demanda Real")
        st.plotly_chart(fig_lluvia, use_container_width=True)
    else:
        st.warning("No se registran variaciones de consumo superiores a cero para esta combinación de filtros.")

# ==========================================================
# TAB 2: VISTA MUNICIPAL
# ==========================================================
with tab2:
    st.header(f"Desglose Territorial: {depto_seleccionado}")
    
    if len(df_muni_filtrado) > 0:
        st.subheader("Municipios con mayor consumo (Top 10)")
        top_munis = df_muni_filtrado.groupby("municipio")["demanda_municipio_est_gwh"].sum().reset_index().sort_values(by="demanda_municipio_est_gwh", ascending=False).head(10)
        
        fig_bar = px.bar(
            top_munis, x="demanda_municipio_est_gwh", y="municipio", orientation="h",
            title="Top Municipios con Mayor Demanda Energética Real en Festivos",
            labels={'demanda_municipio_est_gwh': 'Consumo Acumulado (GWh)', 'municipio': 'Entidad Territorial'}
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Municipios con mayor error promedio")
        col_error = "error_absolute" if "error_absolute" in df_muni_filtrado.columns else "error_absoluto"
        top_error = df_muni_filtrado.groupby("municipio")[col_error].mean().reset_index().sort_values(by=col_error, ascending=False).head(10)
        
        fig_error = px.bar(
            top_error, x=col_error, y="municipio", orientation="h",
            title="Desviación Absoluta Promedio del Modelo por Región",
            labels={col_error: 'Error Absoluto Promedio (GWh)', 'municipio': 'Entidad Territorial'}
        )
        fig_error.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_error, use_container_width=True)
    else:
        st.info("No hay información de sub-municipios disponible para esta selección.")

# ==========================================================
# TAB 3: MODELO PREDICTIVO
# ==========================================================
with tab3:
    st.header("Métricas del Modelo Predictivo (Random Forest)")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Coeficiente de Determinación (R²)", "0.9302")
        st.metric("Error Porcentual Absoluto Medio (MAPE)", "16.82%")
        st.metric("Error Absoluto Medio (MAE)", "0.0267 GWh")
        st.metric("Error Cuadrático Medio (RMSE)", "0.1795 GWh")

    with col2:
        st.markdown("""
        ### Detalles Técnicos del Algoritmo
        - **Conjunto de Entrenamiento:** Registros diarios continuos (2022-2025).
        - **Conjunto de Validación:** Festivos nacionales del primer semestre de 2026.
        - **Target Predictivo:** Demanda Eléctrica por Nodo de Distribución.
        """)

    st.write("---")
    st.subheader("Importancia Relativa de las Características (Feature Importance)")
    fig_imp = px.bar(df_importancia, x="Importancia", y="Caracteristica", orientation="h", title="Peso de las Variables en las Decisiones del Árbol")
    fig_imp.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_imp, use_container_width=True)

# ==========================================================
# TAB 4: SECTORES ECONÓMICOS
# ==========================================================
with tab4:
    st.header("🔥 Matriz y Estructura del Consumo Sectorial Histórico (2022-2026)")
    
    columnas_industrias = [col for col in df_sector_hist.columns if col not in ['fecha', 'departamento']]
    
    st.subheader("1. Mapa de Calor Global: Intensidad Energética por Sector")
    df_heat_hist = df_sector_hist.groupby('departamento')[columnas_industrias].sum().reset_index()
    df_heat_melted_hist = df_heat_hist.melt(id_vars='departamento', var_name='Sector Industrial', value_name='Consumo_Acumulado_GWh')
    
    fig_heatmap_hist = px.density_heatmap(
        df_heat_melted_hist, x="Sector Industrial", y="departamento", z="Consumo_Acumulado_GWh",
        color_continuous_scale="Viridis", title="Demanda Eléctrica Acumulada por Actividad Industrial Comercial"
    )
    st.plotly_chart(fig_heatmap_hist, use_container_width=True)
    
    st.write("---")
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("2. Distribución Regional por Actividad")
        sector_seleccionado = st.selectbox("Seleccione un Sector Industrial para analizar:", columnas_industrias)
        df_ranking_hist = df_heat_hist[['departamento', sector_seleccionado]].sort_values(by=sector_seleccionado, ascending=False).head(10)
        
        fig_ranking_hist_bar = px.bar(df_ranking_hist, x=sector_seleccionado, y='departamento', orientation='h', title=f"Top 10 Regiones Líderes en {sector_seleccionado}")
        fig_ranking_hist_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_ranking_hist_bar, use_container_width=True)
        
    with col_der:
        st.subheader("3. Dominancia Eléctrica en la Matriz Regional")
        df_heat_hist['Sector Predominante'] = df_heat_hist[columnas_industrias].idxmax(axis=1)
        df_heat_hist['Consumo Máximo (GWh)'] = df_heat_hist[columnas_industrias].max(axis=1)
        
        tabla_dominante_hist = df_heat_hist[['departamento', 'Sector Predominante', 'Consumo Máximo (GWh)']].sort_values(by='Consumo Máximo (GWh)', ascending=False)
        tabla_dominante_hist.columns = ['Departamento', 'Actividad Económica Líder', 'Consumo Histórico (GWh)']
        st.dataframe(tabla_dominante_hist, use_container_width=True, hide_index=True)

# ==========================================================
# TAB 5: CONCLUSIONES
# ==========================================================
with tab5:
    st.header("Conclusiones Académicas")
    st.markdown("""
    - **Precisión Estructural:** El modelo presenta un ajuste óptimo ($R^2 = 0.9302$), logrando capturar las dinámicas de desaceleración comercial en días festivos nacionales de manera robusta.
    - **Elasticidad Climática:** La precipitación promedio departamental mostró un impacto marginal frente al peso estructural de las variables geográficas fijas (municipio/departamento), sugiriendo que la demanda en días no laborables responde a inercias comerciales rígidas y no a fluctuaciones meteorológicas de corto plazo.
    """)
    st.success("Análisis Finalizado Exitosamente.")
