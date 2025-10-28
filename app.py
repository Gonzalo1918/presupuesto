# app.py
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image
import tempfile
import datetime
import pandas as pd
import os

st.set_page_config(page_title="Generador de Presupuestos", page_icon="💰", layout="wide")

# ----------------- Menú lateral -----------------
st.sidebar.title("📋 Menú principal")
modo = st.sidebar.radio("Seleccioná qué querés generar:", ["Presupuesto", "Remito"])

# Título dinámico
st.title(f"💼 Generador de {modo}s")

# ----------------- Helpers -----------------
def parse_float_tol(s):
    if s is None or str(s).strip() == "":
        raise ValueError("Valor vacío")
    s = str(s).strip().replace("$", "").replace("ARS", "").replace("USD", "").replace(" ", "")
    if s.count(".") > 0 and s.count(",") > 0:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    return float(s)

def parse_int_tol(s):
    if s is None or str(s).strip() == "":
        raise ValueError("Valor vacío")
    return int(round(parse_float_tol(s)))

def format_currency_ar(value):
    try:
        v = float(value)
    except:
        v = 0.0
    entero = int(abs(v))
    dec = abs(v) - entero
    entero_str = f"{entero:,}".replace(",", ".")
    dec_str = f"{dec:.2f}"[1:].replace(".", ",")
    sign = "-" if v < 0 else ""
    return f"{sign}$ {entero_str}{dec_str}"

def format_currency_usd(value):
    try:
        v = float(value)
    except:
        v = 0.0
    entero = int(abs(v))
    dec = abs(v) - entero
    entero_str = f"{entero:,}".replace(",", ".")
    dec_str = f"{dec:.2f}"[1:].replace(".", ",")
    sign = "-" if v < 0 else ""
    return f"{sign}U$D {entero_str}{dec_str}"

def draw_wrapped_text(c, text, x, y, max_width, line_height, font_name="Helvetica", font_size=10):
    words = str(text).split()
    lines, current = [], ""
    for w in words:
        test = current + (" " if current else "") + w
        if c.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    for i, line in enumerate(lines):
        c.drawString(x, y - i * line_height, line)
    return len(lines)

LAST_FILE = "last_presupuesto.txt"

def obtener_proximo_numero():
    try:
        if not os.path.exists(LAST_FILE):
            with open(LAST_FILE, "w") as f:
                f.write("1")
                return 1
        with open(LAST_FILE, "r+") as f:
            n = int(f.read().strip() or 0) + 1
            f.seek(0)
            f.truncate()
            f.write(str(n))
            return n
    except:
        return int(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

def numero_a_formato(n):
    return str(n).zfill(4)

# ----------------- UI -----------------
with st.expander("Datos de la empresa", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        empresa = st.text_input("Empresa", value="Ayrton Neumáticos")
        cuit = st.text_input("CUIT", value="")
    with col2:
        direccion = st.text_input("Dirección", value="Córdoba")
        correo = st.text_input("Correo electrónico", value="ayrtonneumaticos@gmail.com")
    with col3:
        logo_file = st.file_uploader("Subir logo (opcional)", type=["png","jpg","jpeg"])
        logo_preview = None
        if logo_file:
            logo_preview = Image.open(logo_file)

with st.expander("Datos del cliente", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Cliente", value="")
        tipo_id = st.selectbox("Tipo ID", ["CUIT","DNI","CUIL"], index=0)
    with col2:
        numero_id = st.text_input(f"Número de {tipo_id}", value="")
        descripcion = st.text_area("Descripción / Nota", value="", height=80)

with st.expander("Fechas e IVA", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        fecha_emision = st.date_input("Fecha de emisión", value=datetime.date.today())
        fecha_validez = st.date_input("Válido hasta", value=(datetime.date.today() + datetime.timedelta(days=7)))
    with col2:
        iva_input = st.number_input("IVA %", value=0.0, min_value=0.0, max_value=100.0, step=0.5)
    with col3:
        moneda = st.selectbox("Moneda", ["ARS","USD"], index=0)
        cotizacion_input = st.number_input("Cotización USD (ARS)", value=0.0) if moneda == "USD" else 0.0

st.markdown("---")
st.header("Ítems")

if "productos_df" not in st.session_state:
    st.session_state.productos_df = pd.DataFrame({
        "descripcion": [""],
        "cantidad": [1],
        "precio": [0.0],
        "tipo_desc": ["$"],
        "valor_desc": [0.0],
    })

edited_df = st.data_editor(
    st.session_state.productos_df,
    use_container_width=True,
    num_rows="dynamic",
    key="editor_productos",
)

for col in ["cantidad","precio","valor_desc"]:
    if col in edited_df.columns:
        edited_df[col] = pd.to_numeric(edited_df[col], errors='coerce').fillna(0)

def calcular_subtotales(df):
    rows = df.copy()
    rows["base"] = rows["cantidad"] * rows["precio"]
    def calc_desc(row):
        if str(row.get("tipo_desc","$")) == "%":
            return row["base"] * (row.get("valor_desc",0)/100.0)
        return row.get("valor_desc",0)
    rows["desc_monto"] = rows.apply(calc_desc, axis=1)
    rows["subtotal"] = rows["base"] - rows["desc_monto"]
    return rows

rows = calcular_subtotales(edited_df)
subtotal = rows["subtotal"].sum()
descuento_total = rows["desc_monto"].sum()
iva_val = float(iva_input or 0)
iva_total = subtotal * iva_val / 100.0
total_general = subtotal + iva_total

st.markdown("### Resumen")
col1, col2, col3, col4 = st.columns(4)
col1.write(f"Subtotal: {format_currency_ar(subtotal)}")
col2.write(f"Descuentos: -{format_currency_ar(descuento_total)}")
col3.write(f"IVA ({iva_val}%): {format_currency_ar(iva_total)}")
col4.markdown(f"### TOTAL: {format_currency_ar(total_general)}")

# ----------------- Mostrar/Ocultar -----------------
st.markdown("---")
st.header("Mostrar/Ocultar campos en PDF")
col_show_1, col_show_2 = st.columns(2)
with col_show_1:
    mostrar_logo = st.checkbox("Mostrar logo", value=True)
    mostrar_cuit = st.checkbox("Mostrar CUIT/CUIL", value=True)
    mostrar_dir = st.checkbox("Mostrar dirección", value=True)
    mostrar_correo = st.checkbox("Mostrar correo", value=True)
with col_show_2:
    mostrar_fecha_emision = st.checkbox("Mostrar fecha de emisión", value=True)
    mostrar_fecha_validez = st.checkbox("Mostrar fecha de validez", value=True)
    mostrar_tipo_numero_id = st.checkbox("Mostrar Tipo/Numero ID", value=True)
    mostrar_descripcion = st.checkbox("Mostrar descripción/note", value=True)

st.markdown("---")

# ----------------- Generar PDF -----------------
def generar_pdf(tipo_doc, **kwargs):
    empresa = kwargs["empresa"]
    cliente = kwargs["cliente"]
    nro = kwargs["nro_presupuesto"]
    moneda = kwargs["moneda"]
    cotizacion_dolar = kwargs["cotizacion_dolar"]
    logo_image_pil = kwargs["logo_image_pil"]
    items_rows = kwargs["items_rows"]
    subtotal = kwargs["subtotal"]
    descuento_total = kwargs["descuento_total"]
    iva = kwargs["iva"]
    total = kwargs["total"]

    safe_cliente = (cliente or "cliente").replace(" ", "_")
    nombre_archivo = f"{tipo_doc}_{numero_a_formato(nro)}_{safe_cliente}.pdf"

    tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    archivo = tmpf.name
    tmpf.close()

    c = canvas.Canvas(archivo, pagesize=A4)
    width, height = A4
    left_x = 40
    right_x_total = 520

    # Logo
    if kwargs["mostrar_logo"] and logo_image_pil is not None:
        img = logo_image_pil.copy()
        img.thumbnail((120,120))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img.save(tmp.name)
        c.drawImage(tmp.name, width - 150, height - 110, width=110, preserveAspectRatio=True, mask="auto")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_x, height - 50, empresa.upper())
    c.line(40, height - 60, width - 40, height - 60)

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 100, f"{tipo_doc.upper()} N° {numero_a_formato(nro)}")

    y = height - 130
    c.setFont("Helvetica", 10)
    c.drawString(left_x, y, f"Cliente: {cliente}")
    y -= 20

    for _, it in items_rows.iterrows():
        c.drawString(left_x, y, f"- {it['descripcion']} x{int(it['cantidad'])}")
        c.drawRightString(right_x_total, y, format_currency_ar(it["subtotal"]))
        y -= 15

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right_x_total, y, f"TOTAL: {format_currency_ar(total)}")

    c.showPage()
    c.save()
    return archivo

# ----------------- Botón generar -----------------
if st.button(f"📄 Generar y descargar {modo}"):
    try:
        if not cliente or rows.empty:
            st.warning("Por favor completar cliente e ítems.")
        else:
            nro = obtener_proximo_numero()
            archivo = generar_pdf(
                tipo_doc=modo,
                empresa=empresa,
                cuit=cuit,
                direccion=direccion,
                correo=correo,
                logo_image_pil=logo_preview,
                nro_presupuesto=nro,
                fecha_emision=fecha_emision,
                fecha_validez=fecha_validez,
                cliente=cliente,
                tipo_id=tipo_id,
                numero_id=numero_id,
                descripcion=descripcion,
                items_rows=rows,
                subtotal=subtotal,
                descuento_total=descuento_total,
                iva=iva_val,
                total=total_general,
                mostrar_logo=mostrar_logo,
                mostrar_cuit=mostrar_cuit,
                mostrar_dir=mostrar_dir,
                mostrar_correo=mostrar_correo,
                mostrar_fecha_emision=mostrar_fecha_emision,
                mostrar_fecha_validez=mostrar_fecha_validez,
                mostrar_tipo_numero_id=mostrar_tipo_numero_id,
                mostrar_descripcion=mostrar_descripcion,
                moneda=moneda,
                cotizacion_dolar=cotizacion_input
            )

            with open(archivo, "rb") as f:
                data = f.read()
            fname = os.path.basename(archivo)
            st.download_button("⬇️ Descargar PDF", data=data, file_name=fname, mime="application/pdf")
            st.success(f"{modo} generado correctamente.")
    except Exception as ex:
        st.error(f"Error al generar {modo}: {ex}")






