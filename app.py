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
    base_url = "https://apps.powerapps.com/play/e/default-53a8b0d9-d900-48cc-9d7e-5935dc8d5b17/a/6ca13b56-1edc-49f5-980a-e6a5627f2885?tenantId=53a8b0d9-d900-48cc-9d7e-5935dc8d5b17&key="
    
    encoded_key = urllib.parse.quote(qr_key)
    full_url = base_url + encoded_key
    clean_imei = str(imei).replace(" ", "_")
    clean_model = str(model).replace(" ", "_")
    qr_content = f"{full_url}&info=_IMEI_{clean_imei}_Model_{clean_model}"
    
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=2)
    qr.add_data(qr_content)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = ImageOps.expand(qr_img, border=2, fill='white')
    
    qr_w, qr_h = qr_img.size
    # Mengurangi tinggi total (50 -> 43) untuk mengakomodasi perubahan ukuran
    final_img = Image.new("RGB", (qr_w, qr_h + 43), "white")
    final_img.paste(qr_img, (0, 0))
    
    draw = ImageDraw.Draw(final_img)
    try:
        # Menurunkan size font dari 20 ke 15 (pengurangan ~0.5 size visual)
        font = ImageFont.truetype("arial.ttf", 15)
    except:
        font = ImageFont.load_default()
        
    display_imei = str(imei).split('/')[0]
    bbox_imei = draw.textbbox((0, 0), display_imei, font=font)
    bbox_model = draw.textbbox((0, 0), str(model), font=font)
    
    x_imei = (qr_w - (bbox_imei[2] - bbox_imei[0])) / 2
    x_model = (qr_w - (bbox_model[2] - bbox_model[0])) / 2
    
    draw.text((x_imei, qr_h + 2), display_imei, fill="black", font=font)
    draw.text((x_model, qr_h + 22), str(model), fill="black", font=font)
    
    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    return buf.getvalue()

# --- STREAMLIT UI ---
st.title("📱 QR Code Generator")
password = st.text_input("Enter Password", type="password")

if password == st.secrets["APP_PASSWORD"]:
    mode = st.radio("Select Mode:", ["Manual Input", "Bulk Upload"])
    if mode == "Manual Input":
        imei = st.text_input("IMEI Number")
        model = st.text_input("Device Model")
        qr_key = st.text_input("QR_Key (e.g., IMEI1:004401116782281)")
        
        if st.button("Generate"):
            if imei and model and qr_key:
                img_data = create_qr_image(imei, model, qr_key)
                st.image(img_data)
                st.download_button("Download", img_data, f"{imei.split('/')[0]}.png", "image/png")
    else:
        uploaded_file = st.file_uploader("Upload Excel/CSV", type=["csv", "xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            
            if 'imei' not in df.columns or 'model' not in df.columns:
                st.error("Column 'IMEI' and 'Model' are mandatory!")
                st.stop()
            
            if 'qr_key' not in df.columns:
                df['qr_key'] = 'IMEI1:' + df['imei'].astype(str)
                
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Generate ZIP"):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                        for _, row in df.iterrows():
                            img_bytes = create_qr_image(str(row['imei']), str(row['model']), str(row['qr_key']))
                            zip_file.writestr(f"{str(row['imei']).split('/')[0]}.png", img_bytes)
                    st.download_button("Download ZIP", zip_buffer.getvalue(), "qr_codes.zip", "application/zip")
            with col2:
                if st.button("Generate PDF for Print"):
                    pdf_buffer = io.BytesIO()
                    c = canvas.Canvas(pdf_buffer, pagesize=A4)
                    width, height = A4
                    # Menurunkan ukuran fisik di PDF sebesar 0.25cm (dari 85,94 ke 78,87)
                    qr_w, qr_h = 78, 87 
                    x_margin, y_margin = 30, 30
                    x, y = x_margin, height - y_margin - qr_h
                    
                    for _, row in df.iterrows():
                        img_data = create_qr_image(str(row['imei']), str(row['model']), str(row['qr_key']))
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
    st.warning("Please enter the correct password to access the tool.")
