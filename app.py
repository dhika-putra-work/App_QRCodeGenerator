import streamlit as st
import qrcode
from PIL import Image, ImageDraw, ImageOps, ImageFont
import io
import pandas as pd
import zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import urllib.parse

# Function to generate QR Code
def create_qr_image(imei, model, qr_key):
    base_url = "https://apps.powerapps.com/play/6ca13b56-1edc-49f5-980a-e6a5627f2885?key="
    imei1_only = str(imei).split('/')[0]
    full_url = base_url + urllib.parse.quote(imei1_only)
    
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=2)
    qr.add_data(full_url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = ImageOps.expand(qr_img, border=2, fill='white')
    
    qr_w, qr_h = qr_img.size
    
    # Cek apakah ada dua IMEI
    imei_list = str(imei).split('/')
    has_two_imei = len(imei_list) > 1
    
    # Menentukan tinggi canvas (lebih kecil/dempet)
    extra_height = 55 if has_two_imei else 40
    final_img = Image.new("RGB", (qr_w, qr_h + extra_height), "white")
    final_img.paste(qr_img, (0, 0))
    
    draw = ImageDraw.Draw(final_img)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
        
    # Penempatan teks yang lebih dempet
    if has_two_imei:
        # Label: IMEI1, IMEI2, Model
        draw.text((5, qr_h + 2), f"IMEI1: {imei_list[0]}", fill="black", font=font)
        draw.text((5, qr_h + 18), f"IMEI2: {imei_list[1]}", fill="black", font=font)
        draw.text((5, qr_h + 34), f"Model: {model}", fill="black", font=font)
    else:
        # Label: IMEI1, Model
        draw.text((5, qr_h + 2), f"IMEI1: {imei}", fill="black", font=font)
        draw.text((5, qr_h + 18), f"Model: {model}", fill="black", font=font)
    
    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    return buf.getvalue()

# --- STREAMLIT UI ---
st.title("📱 QR Code Generator")
password = st.text_input("Enter Password", type="password")

if password == st.secrets.get("APP_PASSWORD"):
    mode = st.radio("Select Mode:", ["Manual Input", "Bulk Upload"])
    
    if mode == "Manual Input":
        imei = st.text_input("IMEI Number", placeholder="Example: 123456789012345 or 12345/67890")
        model = st.text_input("Device Model")
        
        qr_key = str(imei).split('/')[0] if imei else ""
        st.text_input("QR_Key (Auto-generated)", value=qr_key, disabled=True)
        
        if st.button("Generate"):
            if imei and model:
                img_data = create_qr_image(imei, model, qr_key)
                st.image(img_data)
                st.download_button("Download", img_data, f"{qr_key}.png", "image/png")
            else:
                st.error("Please fill all required fields!")
    
    else:
        uploaded_file = st.file_uploader("Upload Excel/CSV", type=["csv", "xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            
            if 'imei' not in df.columns or 'model' not in df.columns:
                st.error(f"Column 'IMEI' and 'Model' are mandatory!")
                st.stop()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Generate ZIP"):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                        for _, row in df.iterrows():
                            img_bytes = create_qr_image(str(row['imei']), str(row['model']), "")
                            zip_file.writestr(f"{str(row['imei']).split('/')[0]}.png", img_bytes)
                    st.download_button("Download ZIP", zip_buffer.getvalue(), "qr_codes.zip", "application/zip")
            with col2:
                if st.button("Generate PDF for Print"):
                    pdf_buffer = io.BytesIO()
                    c = canvas.Canvas(pdf_buffer, pagesize=A4)
                    width, height = A4
                    qr_w, qr_h = 100, 120 
                    x_margin, y_margin = 30, 30
                    x, y = x_margin, height - y_margin - qr_h
                    
                    for _, row in df.iterrows():
                        img_data = create_qr_image(str(row['imei']), str(row['model']), "")
                        c.drawImage(ImageReader(io.BytesIO(img_data)), x, y, width=qr_w, height=qr_h)
                        x += qr_w + 10
                        if x + qr_w > width - x_margin:
                            x = x_margin
                            y -= (qr_h + 10)
                        if y < y_margin:
                            c.showPage()
                            x, y = x_margin, height - y_margin - qr_h
                    c.save()
                    st.download_button("Download PDF", pdf_buffer.getvalue(), "qr_codes.pdf", "application/pdf")
else:
    if password:
        st.warning("Incorrect password. Please try again.")
