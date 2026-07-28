import streamlit as st
import qrcode
from PIL import Image, ImageDraw, ImageOps, ImageFont
import io
import pandas as pd
import zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- FUNCTION ---
def create_qr_image(imei_input, model, qr_key):
    # Base URL
    base_url = "https://apps.powerapps.com/play/6ca13b56-1edc-49f5-980a-e6a5627f2885?key="
    qr_content = f"{base_url}{qr_key}"
    
    # Generate QR
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=2)
    qr.add_data(qr_content)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = ImageOps.expand(qr_img, border=2, fill='white')
    
    # Add Text (Rata Tengah)
    qr_w, qr_h = qr_img.size
    final_img = Image.new("RGB", (qr_w, qr_h + 50), "white")
    final_img.paste(qr_img, (0, 0))
    
    draw = ImageDraw.Draw(final_img)
    font = ImageFont.load_default()
    
    # Helper untuk teks rata tengah
    def get_text_width(text, font):
        return draw.textbbox((0, 0), text, font=font)[2]

    # Baris 1: IMEI
    w1 = get_text_width(imei_input, font)
    draw.text(((qr_w - w1) / 2, qr_h + 5), imei_input, fill="black", font=font)
    
    # Baris 2: Model
    w2 = get_text_width(model, font)
    draw.text(((qr_w - w2) / 2, qr_h + 25), model, fill="black", font=font)
    
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
        imei_input = st.text_input("IMEI Number (e.g. 3533... or 3533.../3533...)")
        model = st.text_input("Device Model")
        
        # Logika otomatis ambil IMEI pertama untuk QR_Key
        qr_key = imei_input.split('/')[0] if imei_input else ""
        st.write(f"QR Key (Auto-generated): **{qr_key}**")
        
        if st.button("Generate"):
            if imei_input and model:
                img_data = create_qr_image(imei_input, model, qr_key)
                st.image(img_data)
                st.download_button("Download", img_data, f"{qr_key}.png", "image/png")
            else:
                st.error("Please fill all columns!")

    else:
        uploaded_file = st.file_uploader("Upload Excel/CSV", type=["csv", "xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            
            if 'imei' in df.columns and 'model' in df.columns:
                # Pastikan qr_key diambil dari IMEI pertama
                df['qr_key'] = df['imei'].astype(str).apply(lambda x: x.split('/')[0])
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Generate ZIP"):
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as zf:
                            for _, row in df.iterrows():
                                img = create_qr_image(str(row['imei']), str(row['model']), row['qr_key'])
                                zf.writestr(f"{row['qr_key']}.png", img)
                        st.download_button("Download ZIP", zip_buffer.getvalue(), "qr_codes.zip", "application/zip")
                
                with col2:
                    if st.button("Generate PDF"):
                        pdf_buffer = io.BytesIO()
                        c = canvas.Canvas(pdf_buffer, pagesize=A4)
                        x, y = 30, 750
                        for _, row in df.iterrows():
                            img = create_qr_image(str(row['imei']), str(row['model']), row['qr_key'])
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
