import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile
import datetime
import pandas as pd

st.set_page_config(page_title="Generador de Presupuestos", page_icon="💰")

st.title("💼 Generador de Presupuestos")

# -------------------- DATOS EMPRESA --------------------
st.header("🏢 Datos de la Empresa")
col1, col2 = st.columns(2)
with col1:
    empresa = st.text_input("Nombre de la empresa")
    direccion_empresa = st.text_input("Dirección")
with col2:
    telefono_empresa = st.text_input("Teléfono")
    email_empresa = st.text_input("Correo electrónico")

# -------------------- DATOS CLIENTE --------------------
st.header("👤 Datos del Cliente")
col1, col2 = st.columns(2)
with col1:
    cliente = st.text_input("Nombre del cliente")
    direccion_cliente = st.text_input("Dirección del cliente")
with col2:
    email_cliente = st.text_input("Correo electrónico del cliente")

# -------------------- PRODUCTOS --------------------
st.header("🧾 Productos o Servicios")
st.write("Completá la tabla con los productos, cantidad y precio unitario:")

# DataFrame inicial
if "productos_df" not in st.session_state:
    st.session_state.productos_df = pd.DataFrame(
        {
            "Descripción": ["", "", ""],
            "Cantidad": [1, 1, 1],
            "Precio Unitario": [0.0, 0.0, 0.0],
        }
    )

# Editor interactivo de productos
edited_df = st.data_editor(
    st.session_state.productos_df,
    use_container_width=True,
    num_rows="dynamic",
    key="editor_productos",
)

# Calcular totales
edited_df["Total"] = edited_df["Cantidad"] * edited_df["Precio Unitario"]
subtotal = edited_df["Total"].sum()
iva = subtotal * 0.21  # 21% IVA (editable si querés)
total_general = subtotal + iva

st.write(f"**Subtotal:** ${subtotal:,.2f}")
st.write(f"**IVA (21%):** ${iva:,.2f}")
st.write(f"### 💰 Total: ${total_general:,.2f}")

# -------------------- GENERAR PDF --------------------
if st.button("📄 Generar PDF"):
    if not (empresa and cliente and not edited_df.empty):
        st.warning("Por favor completa los campos requeridos.")
    else:
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        c = canvas.Canvas(temp.name, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica", 11)

        # Encabezado
        c.drawString(50, height - 50, f"Presupuesto - {empresa}")
        c.drawString(50, height - 70, f"Fecha: {datetime.date.today().strftime('%d/%m/%Y')}")
        c.drawString(50, height - 90, f"Tel: {telefono_empresa} | Email: {email_empresa}")

        # Datos del cliente
        c.drawString(50, height - 130, f"Cliente: {cliente}")
        c.drawString(50, height - 150, f"Dirección: {direccion_cliente}")
        c.drawString(50, height - 170, f"Correo: {email_cliente}")

        # Tabla de productos
        y = height - 210
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, "Descripción")
        c.drawString(300, y, "Cantidad")
        c.drawString(380, y, "P.Unitario")
        c.drawString(470, y, "Total")
        c.setFont("Helvetica", 11)
        y -= 20

        for _, row in edited_df.iterrows():
            c.drawString(50, y, str(row["Descripción"]))
            c.drawString(310, y, str(row["Cantidad"]))
            c.drawString(380, y, f"${row['Precio Unitario']:,.2f}")
            c.drawString(470, y, f"${row['Total']:,.2f}")
            y -= 20
            if y < 100:
                c.showPage()
                y = height - 100

        # Totales
        c.setFont("Helvetica-Bold", 12)
        c.drawString(380, y - 20, f"Subtotal: ${subtotal:,.2f}")
        c.drawString(380, y - 40, f"IVA (21%): ${iva:,.2f}")
        c.drawString(380, y - 60, f"Total: ${total_general:,.2f}")

        # Pie de página
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(50, 50, "Gracias por su confianza.")
        c.showPage()
        c.save()

        with open(temp.name, "rb") as file:
            st.download_button(
                label="⬇️ Descargar PDF",
                data=file,
                file_name=f"Presupuesto_{cliente}.pdf",
                mime="application/pdf",
            )
