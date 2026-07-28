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
import requests

# --- CONFIG & CACHE ---
@st.cache_data
def shorten_url(url):
    try:
        api_url = f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(url)}"
        response = requests.get(api_url, timeout=5)
        return response.text if response.status_code == 200 else url
    except:
        return url

def create_qr_image(imei, model, raw_key):
    # Membersihkan key: ambil angka saja jika ada prefix seperti 'IMEI1:'
    clean_key = str(raw_key).split(':')[-1]
    
    # URL baru sesuai permintaan
    base_url = "https://apps.powerapps.com/play/6ca13b56-1edc-49f5-980a-e6a5627f2885?key="
    full_url = f"{base_url}{clean_key}&info=_IMEI_{str(imei).replace(' ', '_')}_Model_{str(model).replace(' ', '_')}"
    
    short_url = shorten_url(full_url)

    # Generate QR
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=5, border=2)
    qr.add_data(short_url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = ImageOps.expand(qr_img, border=2, fill='white')
    
    # Add Text
    qr_w, qr_h = qr_img.size
    final_img = Image.new("RGB", (qr_w, qr_h + 50), "white")
    final_img.paste(qr_img, (0, 0))
    
    draw = ImageDraw.Draw(final_img)
    font = ImageFont.load_default()
    
    display_imei = str(imei).split('/')[0]
    draw.text((10, qr_h + 5), f"IMEI: {display_imei}", fill="black", font=font)
    draw.text((10, qr_h + 25), f"Model: {model}", fill="black", font=font)
    
    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    return buf.getvalue()

# --- UI ---
st.set_page_config(page_title="QR Generator", page_icon="📱")
st.title("📱 QR Code Generator")

password = st.text_input("Enter Password", type="password")
app_password = st.secrets.get("APP_PASSWORD", "!doc-rmn3")

if password == app_password:
    mode = st.radio("Select Mode:", ["Manual Input", "Bulk Upload"])

    if mode == "Manual Input":
        imei = st.text_input("IMEI Number")
        model = st.text_input("Device Model")
        qr_key = st.text_input("QR_Key (e.g. 004401116782281)", value=imei)
        
        if st.button("Generate"):
            if imei and model and qr_key:
                img_data = create_qr_image(imei, model, qr_key)
                st.image(img_data)
                st.download_button("Download", img_data, f"{imei.split('/')[0]}.png", "image/png")
            else:
                st.error("Please fill all columns!")

    else:
        uploaded_file = st.file_uploader("Upload Excel/CSV", type=["csv", "xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            
            if 'imei' in df.columns and 'model' in df.columns:
                if 'qr_key' not in df.columns: df['qr_key'] = df['imei']
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Generate ZIP"):
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as zf:
                            for _, row in df.iterrows():
                                img = create_qr_image(row['imei'], row['model'], row['qr_key'])
                                zf.writestr(f"{str(row['imei']).split('/')[0]}.png", img)
                        st.download_button("Download ZIP", zip_buffer.getvalue(), "qr_codes.zip", "application/zip")
                
                with col2:
                    if st.button("Generate PDF"):
                        pdf_buffer = io.BytesIO()
                        c = canvas.Canvas(pdf_buffer, pagesize=A4)
                        x, y = 30, 750
                        for _, row in df.iterrows():
                            img = create_qr_image(row['imei'], row['model'], row['qr_key'])
                            c.drawImage(ImageReader(io.BytesIO(img)), x, y, width=100, height=110)
                            x += 120
                            if x > 500: x = 30; y -= 130
                            if y < 100: c.showPage(); y = 750
                        c.save()
                        st.download_button("Download PDF", pdf_buffer.getvalue(), "qr_codes.pdf", "application/pdf")
            else:
                st.error("Missing 'imei' or 'model' column!")
else:
    if password: st.warning("Incorrect Password")
