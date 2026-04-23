import streamlit as st
import pandas as pd
import numpy as np

# Configuración de la página
st.set_page_config(page_title="App Mingas", page_icon="👩‍🍳")
st.title("Calculadora de Sellos - Mingas 👩‍🍳")

# --- CARGAR BASE DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel("IngredientesBaseApp.v1.xlsx")
        # --- LIMPIEZA CLAVE: Rellenar vacíos con 0 y limpiar nombres ---
        df = df.fillna(0) 
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"❌ No encontré el archivo Excel. Asegúrate de que se llame 'IngredientesBaseApp.v1.xlsx'")
        return None

df_ingredientes = cargar_datos()
if df_ingredientes is not None:
    lista_ingredientes = sorted(df_ingredientes["Ingrediente"].dropna().astype(str).unique().tolist())
else:
    lista_ingredientes = []

# --- INICIALIZAR MEMORIA ---
for key, default in [
    ('paso', 1), ('carrito', []), ('cantidades', {}), 
    ('num_porciones', 1), ('peso_porcion', 100.0), ('desc_porcion', "1 porción")
]:
    if key not in st.session_state: st.session_state[key] = default

# --- PASO 1: SELECCIÓN ---
if st.session_state.paso == 1:
    st.subheader("Paso 1: Selecciona tus ingredientes")
    seleccion = st.selectbox("Busca un ingrediente:", options=["Selecciona..."] + lista_ingredientes)
    
    if st.button("Agregar a la receta"):
        if seleccion != "Selecciona..." and seleccion not in st.session_state.carrito:
            st.session_state.carrito.append(seleccion)
            st.session_state.cantidades[seleccion] = 0.0 
            st.success(f"¡{seleccion} agregado!")

    st.write("---")
    if st.session_state.carrito:
        st.write("### 🛒 Tu lista:")
        for item in st.session_state.carrito:
            col1, col2 = st.columns([4, 1])
            col1.write(f"✅ {item}")
            if col2.button("Eliminar", key=f"del_{item}"):
                st.session_state.carrito.remove(item)
                st.rerun()
        if st.button("Siguiente: Cantidades ➡️"):
            st.session_state.paso = 2
            st.rerun()

# --- PASO 2: GRAMOS ---
elif st.session_state.paso == 2:
    st.subheader("Paso 2: ¿Cuánto usaste?")
    for item in st.session_state.carrito:
        st.session_state.cantidades[item] = st.number_input(f"Gramos/ml de {item}:", min_value=0.0, value=float(st.session_state.cantidades.get(item, 0.0)), step=5.0)
    
    col_at, col_sig = st.columns(2)
    if col_at.button("⬅️ Volver"): st.session_state.paso = 1; st.rerun()
    if col_sig.button("Siguiente: Porciones ➡️"): st.session_state.paso = 3; st.rerun()

# --- PASO 3: RENDIMIENTO Y PORCIÓN ---
elif st.session_state.paso == 3:
    st.subheader("Paso 3: Rendimiento y Porciones")
    st.write("Diferenciemos el total producido de la porción sugerida.")
    
    # 1. ¿Cuánto salió en total?
    st.session_state.peso_total_receta = st.number_input(
        "⚖️ ¿Cuánto pesa tu producto en total? (Peso Neto en gramos)", 
        min_value=1.0, 
        value=500.0,
        step=10.0,
        help="Ej: Si llenaste un frasco de mermelada de 250g, pon 250."
    )
    
    # 2. ¿Cuánto es la porción?
    st.session_state.peso_porcion = st.number_input(
        "🥄 Tamaño de la porción (en gramos)", 
        min_value=1.0, 
        value=15.0,
        step=1.0,
        help="Ej: Para mermeladas la porción suele ser 15g (1 cucharadita)."
    )
    
    # 3. Descripción
    st.session_state.desc_porcion = st.text_input(
        "✍️ Descripción de la porción", 
        value="1 cucharadita"
    )
    
    # Cálculo automático de porciones para mostrar al usuario
    num_porciones_calc = st.session_state.peso_total_receta / st.session_state.peso_porcion
    st.info(f"💡 Tu envase tendrá aproximadamente **{num_porciones_calc:.1f}** porciones.")

    st.write("---")
    col_at, col_sig = st.columns(2)
    if col_at.button("⬅️ Volver"): st.session_state.paso = 2; st.rerun()
    if col_sig.button("Siguiente: Calcular Sellos ➡️"): st.session_state.paso = 4; st.rerun()

# --- PASO 4: ETIQUETA ---
elif st.session_state.paso == 4:
    st.subheader("Paso 4: Etiqueta Nutricional")

    def find_col(name):
        for c in df_ingredientes.columns:
            if name.lower() in c.lower(): return c
        return None

    cols = {
        'ener': find_col('Energ'), 'prot': find_col('Prote'), 
        'g_tot': find_col('Grasas totales'), 'g_sat': find_col('saturada'),
        'hc': find_col('Hidratos'), 'az': find_col('Azúcar'), 'sod': find_col('Sodio')
    }

    totales = {k: 0.0 for k in cols.keys()}
    for item in st.session_state.carrito:
        cant = st.session_state.cantidades[item]
        fila = df_ingredientes[df_ingredientes["Ingrediente"] == item]
        if not fila.empty:
            for k, col_name in cols.items():
                if col_name:
                    valor = pd.to_numeric(fila[col_name].values[0], errors='coerce')
                    if np.isnan(valor): valor = 0.0
                    totales[k] += (valor / 100) * cant

    peso_total = st.session_state.num_porciones * st.session_state.peso_porcion
    
    def calc(val): 
        if peso_total == 0: return 0.0, 0.0
        p100 = (val / peso_total * 100)
        p_porc = (val / st.session_state.num_porciones)
        return p100, p_porc

    res = {k: calc(v) for k, v in totales.items()}

    # TABLA HTML
    st.markdown(f"""
    <div style="font-family: Arial; border: 2px solid black; padding: 15px; width: 350px; background: white; color: black;">
        <h3 style="text-align: center; border-bottom: 2px solid black; margin: 0 0 10px 0;">INFORMACIÓN NUTRICIONAL</h3>
        <p style="margin: 2px 0;"><b>Porción:</b> {st.session_state.desc_porcion} ({st.session_state.peso_porcion}g)</p>
        <p style="margin: 2px 0;"><b>Porciones por envase:</b> Aprox. {st.session_state.num_porciones}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px; color: black;">
            <tr style="border-bottom: 1px solid black;">
                <th style="text-align: left;"></th>
                <th style="text-align: right;">100g</th>
                <th style="text-align: right;">1 porc.</th>
            </tr>
            <tr><td><b>Energía (kcal)</b></td><td align="right">{res['ener'][0]:.1f}</td><td align="right">{res['ener'][1]:.1f}</td></tr>
            <tr><td><b>Proteínas (g)</b></td><td align="right">{res['prot'][0]:.1f}</td><td align="right">{res['prot'][1]:.1f}</td></tr>
            <tr><td><b>Grasas Totales (g)</b></td><td align="right">{res['g_tot'][0]:.1f}</td><td align="right">{res['g_tot'][1]:.1f}</td></tr>
            <tr><td style="padding-left:10px;">- Grasas Sat. (g)</td><td align="right">{res['g_sat'][0]:.1f}</td><td align="right">{res['g_sat'][1]:.1f}</td></tr>
            <tr><td><b>H. de C. disp. (g)</b></td><td align="right">{res['hc'][0]:.1f}</td><td align="right">{res['hc'][1]:.1f}</td></tr>
            <tr><td style="padding-left:10px;">- Azúcares tot. (g)</td><td align="right">{res['az'][0]:.1f}</td><td align="right">{res['az'][1]:.1f}</td></tr>
            <tr style="border-top: 2px solid black;">
                <td><b>Sodio (mg)</b></td>
                <td align="right"><b>{res['sod'][0]:.1f}</b></td>
                <td align="right"><b>{res['sod'][1]:.1f}</b></td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # SELLOS
    st.write("### 🛑 Sellos correspondientes:")
    sellos_activos = []
    if res['ener'][0] > 275: sellos_activos.append("CALORÍAS")
    if res['az'][0] > 10: sellos_activos.append("AZÚCARES")
    if res['g_sat'][0] > 4: sellos_activos.append("GRASAS SATURADAS")
    if res['sod'][0] > 400: sellos_activos.append("SODIO")

    if not sellos_activos:
        st.success("✅ Receta libre de sellos")
    else:
        urls = {
            "CALORÍAS": "https://codigoele.cl/wp-content/uploads/2020/06/ALTO-EN-CALORIAS_generica-286x300-1.jpg",
            "AZÚCARES": "https://codigoele.cl/wp-content/uploads/2020/06/ALTO-EN-AZUCARES_generica-286x300-1.jpg",
            "GRASAS SATURADAS": "https://codigoele.cl/wp-content/uploads/2020/06/ALTO-EN-GRASAS-SATURADAS_generica-286x300-1.jpg",
            "SODIO": "https://codigoele.cl/wp-content/uploads/2020/06/ALTO-EN-SODIO_generica-286x300-1.jpg"
        }
        cols_sellos = st.columns(len(sellos_activos))
        for i, s in enumerate(sellos_activos):
            cols_sellos[i].image(urls[s], width=100)

    st.write("---")
    # BOTÓN FINAL CORREGIDO
    if st.button("🔄 Empezar Nueva Receta"):
        st.session_state.paso = 1
        st.session_state.carrito = []
        st.session_state.cantidades = {}
        st.session_state.num_porciones = 1
        st.session_state.peso_porcion = 100.0
        st.session_state.desc_porcion = "1 porción"
        st.rerun()