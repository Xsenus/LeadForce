import os
import uuid
import platform
import subprocess
import traceback
from datetime import datetime
from flask import Flask, request, send_file, jsonify
from io import BytesIO
import zipfile
from num2words import num2words 
from typing import Dict, Iterable

from docx import Document
from docx.shared import Mm

from payment_qr import build_payment_qr

if platform.system() == "Windows":
    import pythoncom
    import win32com.client

TEMPLATE_PATH = "./Templates/LeadsForce_v0.docx"
OUTPUT_DIR = "./output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PAYMENT_QR_MARKER = "__PAYMENT_QR_PLACEHOLDER__"

PLACEHOLDERS = [
    "ID", "INVOICE_DATE", "CUSTOMER", "PRODUCT", "SUM", "AMOUNT_IN_WORDS",
    "DEAL", "SERVICE", "CITY", "LEAD_SUM", "LEAD_COST", "REVENUE", "PRICE",
    "EMAIL", "PHONE", "NAME", "INN", "COMPANYNAME", "PAYMENT_QR"
]

app = Flask(__name__)

def fill_template_xml(template_path: str, replacements: dict, output_path: str):
    with zipfile.ZipFile(template_path, 'r') as zin:
        with zipfile.ZipFile(output_path, 'w') as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == 'word/document.xml':
                    xml = data.decode('utf-8')
                    for key, value in replacements.items():
                        xml = xml.replace(f'{{{{{key}}}}}', value)
                    data = xml.encode('utf-8')
                zout.writestr(item, data)

def convert_to_pdf(input_docx: str, output_dir: str):
    if platform.system() == "Windows":
        pythoncom.CoInitialize()
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            abs_input = os.path.abspath(input_docx).replace("/", "\\")
            doc = word.Documents.Open(abs_input)
            output_pdf = os.path.splitext(abs_input)[0] + ".pdf"
            doc.SaveAs(output_pdf, FileFormat=17)
            doc.Close(False)
            word.Quit()
            return output_pdf
        finally:
            pythoncom.CoUninitialize()
    else:
        subprocess.run([
            "soffice", "--headless", "--convert-to", "pdf",
            "--outdir", output_dir, input_docx
        ], check=True)
        return os.path.splitext(input_docx)[0] + ".pdf"

def zip_single_file(file_path, arcname):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.write(file_path, arcname=arcname)
    buffer.seek(0)
    return buffer

def zip_two_files(file1_path, file2_path, name1, name2):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.write(file1_path, arcname=name1)
        zf.write(file2_path, arcname=name2)
    buffer.seek(0)
    return buffer

MONTHS_RU = {
    '01': 'января', '02': 'февраля', '03': 'марта',
    '04': 'апреля', '05': 'мая', '06': 'июня',
    '07': 'июля', '08': 'августа', '09': 'сентября',
    '10': 'октября', '11': 'ноября', '12': 'декабря'
}

def format_invoice_date(date_str):
    try:
        day, month, year = date_str.strip().split('.')
        return f"{int(day)} {MONTHS_RU[month]} {year} г."
    except:
        return date_str  # fallback если не смогли

def get_request_context():
    args = request.args

    price_str = args.get("price", "").replace(",", ".").strip()
    price_text = args.get("price_text", "").strip()

    # Обработка даты
    bill_date_raw = args.get("bill_date", "").strip()
    bill_date = bill_date_raw.split()[0] if bill_date_raw and " " in bill_date_raw else ""
    invoice_date = bill_date or args.get("invoiceDate", "").strip()
    if not invoice_date:
        invoice_date = datetime.today().strftime('%d.%m.%Y')

    # Генерация суммы прописью
    try:
        if not price_text:
            price_float = float(price_str)
            rub = int(price_float)
            kop = int(round((price_float - rub) * 100))
            amount_in_words = f"{num2words(rub, lang='ru').capitalize()} рублей {kop:02d} копеек"
        else:
            amount_in_words = price_text
    except:
        amount_in_words = ""

    # Заказчик
    customer_parts = [
        args.get("name", "").strip(),
        args.get("phone", "").strip(),
        args.get("email", "").strip(),
        args.get("inn", "").strip(),
        args.get("companyName", "").strip()
    ]
    customer = ", ".join(filter(None, customer_parts))

    # Товар
    product_service = args.get("service", "").strip()
    product = f"Система привлечения клиентов / {product_service}" if product_service else "Система привлечения клиентов"

    replacements = {
        "ID": args.get("deal", str(uuid.uuid4())[:8]),
        "INVOICE_DATE": format_invoice_date(invoice_date),
        "CUSTOMER": customer,
        "PRODUCT": product,
        "SUM": price_str,
        "AMOUNT_IN_WORDS": amount_in_words,
        "DEAL": args.get("deal", ""),
        "SERVICE": args.get("service", ""),
        "CITY": args.get("city", ""),
        "LEAD_SUM": args.get("lead_sum", ""),
        "LEAD_COST": args.get("lead_cost", ""),
        "REVENUE": args.get("revenue", ""),
        "PRICE": price_str,
        "EMAIL": args.get("email", ""),
        "PHONE": args.get("phone", ""),
        "NAME": args.get("name", ""),
        "INN": args.get("inn", ""),
        "COMPANYNAME": args.get("companyName", "")
    }

    qr_image = None
    if args.get("qr_enabled", "1").lower() not in {"0", "false", "no"}:
        qr_image = build_payment_qr(args, price_str)

    if qr_image:
        replacements["PAYMENT_QR"] = PAYMENT_QR_MARKER
    else:
        replacements["PAYMENT_QR"] = ""

    assets = {}
    if qr_image:
        assets["PAYMENT_QR"] = qr_image

    return replacements, assets


def build_doc(replacements: dict, assets: Dict[str, bytes]):
    file_id = str(uuid.uuid4())
    docx_path = os.path.join(OUTPUT_DIR, f"{file_id}.docx")
    fill_template_xml(TEMPLATE_PATH, replacements, docx_path)
    if qr_bytes := assets.get("PAYMENT_QR"):
        embed_qr_image(docx_path, PAYMENT_QR_MARKER, qr_bytes)
    pdf_path = convert_to_pdf(docx_path, OUTPUT_DIR)
    return docx_path, pdf_path


def iter_paragraphs(container) -> Iterable:
    for paragraph in container.paragraphs:
        yield paragraph
    if hasattr(container, "tables"):
        for table in container.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from iter_paragraphs(cell)


def embed_qr_image(docx_path: str, marker: str, image_bytes: bytes, width_mm: int = 35) -> None:
    document = Document(docx_path)
    replaced = False

    for paragraph in iter_paragraphs(document):
        replaced = replace_marker_with_image(paragraph, marker, image_bytes, width_mm) or replaced

    if replaced:
        document.save(docx_path)


def replace_marker_with_image(paragraph, marker: str, image_bytes: bytes, width_mm: int) -> bool:
    replaced = False
    runs = list(paragraph.runs)
    for run in runs:
        while marker in run.text:
            replaced = True
            before, _, after = run.text.partition(marker)
            run.text = before

            image_run = paragraph.add_run()
            run._element.addnext(image_run._element)
            image_run.add_picture(BytesIO(image_bytes), width=Mm(width_mm))

            if after:
                after_run = paragraph.add_run(after)
                image_run._element.addnext(after_run._element)
                run = after_run
            else:
                break
    return replaced

@app.route("/Document/GetPdf")
def get_pdf():
    try:
        replacements, assets = get_request_context()
        _, pdf_path = build_doc(replacements, assets)
        return send_file(pdf_path, download_name="document.pdf", mimetype="application/pdf")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/Document/GetDocx")
def get_docx():
    try:
        replacements, assets = get_request_context()
        docx_path, _ = build_doc(replacements, assets)
        return send_file(docx_path, download_name="document.docx", mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/Document/GetPdfZip")
def get_pdf_zip():
    try:
        replacements, assets = get_request_context()
        _, pdf_path = build_doc(replacements, assets)
        zip_buffer = zip_single_file(pdf_path, "document.pdf")
        return send_file(zip_buffer, download_name="document_pdf.zip", mimetype="application/zip", as_attachment=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/Document/GetDocxZip")
def get_docx_zip():
    try:
        replacements, assets = get_request_context()
        docx_path, _ = build_doc(replacements, assets)
        zip_buffer = zip_single_file(docx_path, "document.docx")
        return send_file(zip_buffer, download_name="document_docx.zip", mimetype="application/zip", as_attachment=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/Document/GetAllZip")
def get_all_zip():
    try:
        replacements, assets = get_request_context()
        docx_path, pdf_path = build_doc(replacements, assets)
        zip_buffer = zip_two_files(docx_path, pdf_path, "document.docx", "document.pdf")
        return send_file(zip_buffer, download_name="documents_full.zip", mimetype="application/zip", as_attachment=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=12346, threaded=False)
