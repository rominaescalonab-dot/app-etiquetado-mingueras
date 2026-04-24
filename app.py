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

# --- PASO 2: CANTIDADES (Gramos o ml) ---
elif st.session_state.paso == 2:
    st.subheader("Paso 2: ¿Cuánto usaste?")
    st.write("Ingresa las cantidades para cada ingrediente:")

    for item in st.session_state.carrito:
        # Buscamos el ingrediente en el Excel
        fila = df_ingredientes[df_ingredientes["Ingrediente"] == item]
        unidad = "gramos" # Por defecto
        
        # Verificamos la columna 'Tipo'
        if not fila.empty and 'Tipo' in df_ingredientes.columns:
            tipo_valor = str(fila['Tipo'].values[0]).lower().strip()
            if "liquido" in tipo_valor or "líquido" in tipo_valor:
                unidad = "ml"
        
        # El número: Forzamos a que sea INT (Entero) para que NO salgan los decimales
        valor_guardado = st.session_state.cantidades.get(item, 0)
        
        st.session_state.cantidades[item] = st.number_input(
            f"Cantidad de {item} ({unidad}):", 
            min_value=0, 
            value=int(valor_guardado), 
            step=1,
            format="%d",
            key=f"input_new_{item}"
        )
        
        # Punto de mil chileno (Ayuda visual)
        if st.session_state.cantidades[item] >= 1000:
            formateado = f"{st.session_state.cantidades[item]:,}".replace(",", ".")
            st.caption(f"✅ Registrado: {formateado} {unidad}")

    st.write("---")
    col_at, col_sig = st.columns(2)
    if col_at.button("⬅️ Volver"): st.session_state.paso = 1; st.rerun()
    if col_sig.button("Siguiente: Porciones ➡️"): st.session_state.paso = 3; st.rerun()

# --- PASO 3: RENDIMIENTO Y PORCIONES ---
elif st.session_state.paso == 3:
    st.subheader("Paso 3: Rendimiento y Porciones")
    st.write("Definamos cuánto producto obtuviste y cuál es la porción sugerida.")

    st.markdown("#### 📦 Sobre el Producto Terminado")
    # 1. ¿Cuántos productos salieron?
    st.session_state.num_unidades = st.number_input(
        "¿Cuántos productos salieron en total?", 
        min_value=1, 
        value=st.session_state.get('num_unidades', 1),
        step=1,
        help="Ej: Si de la olla sacaste 20 mermeladas, pon 20."
    )
    
    # 2. ¿Cuánto pesa cada producto?
    st.session_state.peso_por_unidad = st.number_input(
        "¿Cuánto pesa cada producto? (Peso neto en gramos o ml)", 
        min_value=1.0, 
        value=st.session_state.get('peso_por_unidad', 250.0),
        step=10.0,
        help="Ej: Si la mermelada pesa 250g, pon 250."
    )

    st.markdown("#### 🥄 Sobre la Porción")
    # 3. El peso de la porción (necesario para el cálculo de los sellos)
    st.session_state.peso_porcion = st.number_input(
        "¿Cuánto pesa 1 porción? (en gramos o ml)", 
        min_value=1.0, 
        value=st.session_state.get('peso_porcion', 15.0),
        step=1.0,
        help="Ej: 15g para mermeladas."
    )
    
    # 4. Medida casera (El texto que saldrá en la etiqueta)
    st.session_state.desc_porcion = st.text_input(
        "Medida casera para su porción", 
        value=st.session_state.get('desc_porcion', "1 cucharadita"),
        help="Ej: 1 cucharadita, 1 rebanada, 1 unidad."
    )

    # --- CÁLCULOS AUTOMÁTICOS ---
    # Guardamos el peso total para la memoria interna
    st.session_state.peso_total_receta = st.session_state.num_unidades * st.session_state.peso_por_unidad
    
    # Calculamos cuántas porciones rinde un solo producto
    porciones_calc = st.session_state.peso_por_unidad / st.session_state.peso_porcion
    
    st.info(f"💡 **Resumen:** Hiciste {st.session_state.num_unidades} productos de {st.session_state.peso_por_unidad}g/ml. Cada producto tendrá aproximadamente **{porciones_calc:.1f} porciones**.")

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

    # 1. Sumamos todos los nutrientes de la olla gigante
    totales_olla = {k: 0.0 for k in cols.keys()}
    for item in st.session_state.carrito:
        cant = st.session_state.cantidades[item]
        fila = df_ingredientes[df_ingredientes["Ingrediente"] == item]
        if not fila.empty:
            for k, col_name in cols.items():
                if col_name:
                    valor = pd.to_numeric(fila[col_name].values[0], errors='coerce')
                    if np.isnan(valor): valor = 0.0
                    totales_olla[k] += (valor / 100) * cant

    # 2. Recuperamos los datos del Paso 3
    unidades = st.session_state.get('num_unidades', 1)
    peso_unidad = st.session_state.get('peso_por_unidad', 100.0)
    peso_porcion = st.session_state.get('peso_porcion', 15.0)
    
    # 3. Matemática correcta
    peso_total_olla = unidades * peso_unidad
    porciones_por_envase = peso_unidad / peso_porcion
    
    def calc(val_total_olla): 
        if peso_total_olla == 0: return 0.0, 0.0
        # Nutrientes en 100g de producto final
        p100 = (val_total_olla / peso_total_olla) * 100
        # Nutrientes en 1 porción
        p_porc = (val_total_olla / peso_total_olla) * peso_porcion
        return p100, p_porc

    res = {k: calc(v) for k, v in totales_olla.items()}

    # TABLA HTML
    st.markdown(f"""
    <div style="font-family: Arial; border: 2px solid black; padding: 15px; width: 350px; background: white; color: black;">
        <h3 style="text-align: center; border-bottom: 2px solid black; margin: 0 0 10px 0;">INFORMACIÓN NUTRICIONAL</h3>
        <p style="margin: 2px 0;"><b>Porción:</b> {st.session_state.desc_porcion} ({peso_porcion}g)</p>
        <p style="margin: 2px 0;"><b>Porciones por envase:</b> Aprox. {porciones_por_envase:.0f}</p>
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
    # Usamos los valores por 100g para determinar los sellos
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
    # BOTÓN FINAL
    if st.button("🔄 Empezar Nueva Receta"):
        st.session_state.paso = 1
        st.session_state.carrito = []
        st.session_state.cantidades = {}
        # Limpiamos las nuevas variables también
        for key in ['num_unidades', 'peso_por_unidad', 'peso_porcion', 'desc_porcion']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
