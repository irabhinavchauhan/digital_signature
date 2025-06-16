import os
from flask import Flask, render_template, request, send_from_directory
import fitz  # PyMuPDF
from PIL import Image
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
SIGNED_FOLDER = 'signed_docs'
LOG_FILE = 'audit_logs.txt'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SIGNED_FOLDER, exist_ok=True)

signature_path = None

@app.route("/", methods=["GET", "POST"])
def index():
    global signature_path

    if request.method == "POST":
        # Save signature image if uploaded
        if 'signature' in request.files and request.files['signature'].filename != '':
            signature = request.files['signature']
            signature_path = os.path.join(UPLOAD_FOLDER, signature.filename)
            signature.save(signature_path)

        # Save PDF file and sign it
        if 'pdf' in request.files:
            pdf_file = request.files['pdf']
            pdf_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
            pdf_file.save(pdf_path)

            if not signature_path or not os.path.exists(signature_path):
                return "Signature file is missing. Please upload a signature image.", 400

            signed_pdf = sign_pdf(pdf_path, signature_path)
            log_event(pdf_file.filename, signed_pdf)

            return send_from_directory(SIGNED_FOLDER, signed_pdf, as_attachment=True)

    return render_template("index.html")

def sign_pdf(pdf_path, signature_path):
    pdf = fitz.open(pdf_path)
    signature = Image.open(signature_path).convert("RGBA")

    temp_signature_path = "temp_signature.png"
    signature.save(temp_signature_path)

    for page in pdf:
        rect = page.rect
        page_width, page_height = rect.width, rect.height

        scale = 0.15  # 15% of page width
        sig_display_width = int(page_width * scale)
        sig_display_height = int(sig_display_width * signature.height / signature.width)

        x = page_width - sig_display_width - 30
        y = page_height - sig_display_height - 30

        page.insert_image(
            fitz.Rect(x, y, x + sig_display_width, y + sig_display_height),
            filename=temp_signature_path
        )

    output_filename = f"signed_{os.path.basename(pdf_path)}"
    output_path = os.path.join(SIGNED_FOLDER, output_filename)
    pdf.save(output_path)
    pdf.close()
    return output_filename

def log_event(original_pdf, signed_pdf):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()}: {original_pdf} -> {signed_pdf}\n")

if __name__ == "__main__":
    app.run(debug=True)
