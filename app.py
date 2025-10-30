import base64
import os
import platform
import subprocess
import traceback
import uuid
from datetime import datetime
from io import BytesIO

from typing import Any, Optional, cast

from docx import Document
from docx.shared import Mm
from flask import Flask, jsonify, request, send_file
from num2words import num2words

try:
    import qrcode  # type: ignore[import-not-found]
    from qrcode.constants import ERROR_CORRECT_M  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - handled at runtime
    qrcode = None  # type: ignore[assignment]
    ERROR_CORRECT_M = None  # type: ignore[assignment]

try:
    from PIL import Image  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - handled at runtime
    Image = None  # type: ignore[assignment]
import zipfile

TEMPLATE_PATH = "./Templates/LeadsForce_v0.docx"
OUTPUT_DIR = "./output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PLACEHOLDERS = [
    "ID", "INVOICE_DATE", "CUSTOMER", "PRODUCT", "SUM", "AMOUNT_IN_WORDS",
    "DEAL", "SERVICE", "CITY", "LEAD_SUM", "LEAD_COST", "REVENUE", "PRICE",
    "EMAIL", "PHONE", "NAME", "INN", "COMPANYNAME", "PAYMENT_QR_BASE64",
    "PAYMENT_QR_PAYLOAD"
]

app = Flask(__name__)

DEFAULT_PAYMENT_DETAILS = {
    "Name": "ИП Абакумова Наталья Александровна",
    "PersonalAcc": "40802810200006322048",
    "BankName": "АО «Тинькофф Банк»",
    "BIC": "044525974",
    "CorrespAcc": "30101810145250000974",
    "PayeeINN": "720206359451",
    "Purpose": "Оплата по счету №{{ID}}"
}

QR_QUERY_MAP = {
    "qr_name": "Name",
    "qr_personal_account": "PersonalAcc",
    "qr_bank_name": "BankName",
    "qr_bic": "BIC",
    "qr_correspondent_account": "CorrespAcc",
    "qr_inn": "PayeeINN",
    "qr_kpp": "PayeeKPP",
    "qr_payer_address": "PayerAddress"
}

QR_CODE_PLACEHOLDER = "{{QR_CODE}}"

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
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore

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

def zip_files(file_mappings):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for path, arcname in file_mappings:
            if path and os.path.exists(path):
                zf.write(path, arcname=arcname)
    buffer.seek(0)
    return buffer


def encode_file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


PAYMENT_QR_FIELDS_ORDER = [
    "Name",
    "PersonalAcc",
    "BankName",
    "BIC",
    "CorrespAcc",
    "PayeeINN",
    "PayeeKPP",
    "PayerAddress",
    "Sum",
    "Purpose",
]


DEFAULT_QR_WIDTH_MM = 40


def build_payment_qr_payload(details: dict) -> str:
    parts = ["ST00012"]
    used_keys = set()

    for field in PAYMENT_QR_FIELDS_ORDER:
        value = (details.get(field) or "").strip()
        if value:
            parts.append(f"{field}={value}")
            used_keys.add(field)

    for key, value in details.items():
        if key in used_keys:
            continue
        value = (value or "").strip()
        if value:
            parts.append(f"{key}={value}")

    return "|".join(parts)


def _require_qr_dependencies() -> Optional[str]:
    missing = []
    if qrcode is None:
        missing.append("qrcode")
    if Image is None:
        missing.append("Pillow")
    if missing:
        return ", ".join(missing)
    return None


def generate_payment_qr_image(details: dict, file_id: str) -> tuple[str, str]:
    missing = _require_qr_dependencies()
    if missing:
        raise RuntimeError(
            "Для генерации QR-кода необходимо установить зависимости: "
            f"{missing}. Выполните 'pip install -r requirements.txt'."
        )

    payload = build_payment_qr_payload(details)
    if len(payload) <= len("ST00012"):
        return "", ""

    qr_path = os.path.join(OUTPUT_DIR, f"{file_id}_qr.png")
    qr_module = cast(Any, qrcode)
    error_correction = cast(int, ERROR_CORRECT_M)
    qr = qr_module.QRCode(error_correction=error_correction, box_size=10, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    pil_image = qr_image.get_image() if hasattr(qr_image, "get_image") else qr_image
    if not hasattr(pil_image, "save"):
        raise TypeError("Объект QR-кода не поддерживает сохранение в файл")
    pil_image.save(qr_path, format="PNG")

    return payload, qr_path


def _replace_paragraph_with_image(paragraph, image_path: str, width_mm: float):
    while paragraph.runs:
        paragraph._element.remove(paragraph.runs[0]._r)
    run = paragraph.add_run()
    run.add_picture(image_path, width=Mm(width_mm))


def _replace_in_paragraphs(paragraphs, placeholder: str, image_path: str, width_mm: float) -> bool:
    for paragraph in paragraphs:
        if placeholder in paragraph.text:
            paragraph.text = paragraph.text.replace(placeholder, "")
            _replace_paragraph_with_image(paragraph, image_path, width_mm)
            return True
    return False


def insert_qr_code_into_document(docx_path: str, qr_image_path: str, width_mm: float) -> bool:
    document = Document(docx_path)

    if _replace_in_paragraphs(document.paragraphs, QR_CODE_PLACEHOLDER, qr_image_path, width_mm):
        document.save(docx_path)
        return True

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if _replace_in_paragraphs(cell.paragraphs, QR_CODE_PLACEHOLDER, qr_image_path, width_mm):
                    document.save(docx_path)
                    return True

    return False

MONTHS_RU = {
    '01': 'января', '02': 'февраля', '03': 'марта',
    '04': 'апреля', '05': 'мая', '06': 'июня',
    '07': 'июля', '08': 'августа', '09': 'сентября',
    '10': 'октября', '11': 'ноября', '12': 'декабря'
}


def parse_sum_to_kopecks(price_str: str) -> str:
    normalized = (price_str or "").replace(" ", "").replace(",", ".")
    if not normalized:
        return ""

    try:
        amount = float(normalized)
    except ValueError:
        return ""

    return str(int(round(amount * 100)))


def get_qr_width_mm(args) -> float:
    value = (args.get("qr_width_mm", "") or "").strip()
    if not value:
        return DEFAULT_QR_WIDTH_MM

    try:
        width = float(value.replace(",", "."))
        if width <= 0:
            return DEFAULT_QR_WIDTH_MM
        return width
    except ValueError:
        return DEFAULT_QR_WIDTH_MM


def get_payment_details(args, replacements: dict) -> dict:
    details = DEFAULT_PAYMENT_DETAILS.copy()

    for query_param, payload_key in QR_QUERY_MAP.items():
        value = (args.get(query_param, "") or "").strip()
        if value:
            details[payload_key] = value

    invoice_id = replacements.get("ID", "")

    sum_override = (args.get("qr_sum", "") or "").strip()
    if sum_override:
        details["Sum"] = sum_override
    else:
        auto_sum = parse_sum_to_kopecks(replacements.get("SUM", ""))
        if auto_sum:
            details["Sum"] = auto_sum

    purpose_override = (args.get("qr_purpose", "") or "").strip()
    if purpose_override:
        details["Purpose"] = purpose_override
    else:
        purpose = details.get("Purpose", "")
        if purpose and "{{ID}}" in purpose:
            details["Purpose"] = purpose.replace("{{ID}}", invoice_id)
        elif not purpose and invoice_id:
            details["Purpose"] = f"Оплата по счету №{invoice_id}"

    return details


def format_invoice_date(date_str):
    try:
        day, month, year = date_str.strip().split('.')
        return f"{int(day)} {MONTHS_RU[month]} {year} г."
    except:
        return date_str  # fallback если не смогли

def get_replacements():
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

    return {
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
        "COMPANYNAME": args.get("companyName", ""),
        "PAYMENT_QR_BASE64": "",
        "PAYMENT_QR_PAYLOAD": ""
    }


def prepare_generation_inputs():
    replacements = get_replacements()
    payment_details = get_payment_details(request.args, replacements)
    qr_width_mm = get_qr_width_mm(request.args)
    return replacements, payment_details, qr_width_mm


def build_doc(replacements: dict, payment_details: dict, qr_width_mm: float):
    file_id = str(uuid.uuid4())
    docx_path = os.path.join(OUTPUT_DIR, f"{file_id}.docx")

    replacements_for_template = dict(replacements)
    qr_payload = ""
    qr_path = ""

    try:
        qr_payload, qr_path = generate_payment_qr_image(payment_details, file_id)
    except Exception as qr_error:
        traceback.print_exc()
        replacements_for_template["PAYMENT_QR_PAYLOAD"] = str(qr_error)
        replacements_for_template["PAYMENT_QR_BASE64"] = ""

    if qr_payload and qr_path and os.path.exists(qr_path):
        try:
            replacements_for_template["PAYMENT_QR_PAYLOAD"] = qr_payload
            replacements_for_template["PAYMENT_QR_BASE64"] = encode_file_to_base64(qr_path)
        except Exception:
            traceback.print_exc()

    fill_template_xml(TEMPLATE_PATH, replacements_for_template, docx_path)

    if qr_payload and qr_path and os.path.exists(qr_path):
        try:
            insert_qr_code_into_document(docx_path, qr_path, qr_width_mm)
        except Exception:
            traceback.print_exc()

    pdf_path = convert_to_pdf(docx_path, OUTPUT_DIR)
    return docx_path, pdf_path, qr_path

def _build_service_description() -> dict:
    return {
        "message": "LeadForce Document Generator", 
        "endpoints": {
            "pdf": "/Document/GetPdf",
            "docx": "/Document/GetDocx",
            "zip_pdf": "/Document/GetPdfZip",
            "zip_docx": "/Document/GetDocxZip",
            "zip_all": "/Document/GetAllZip",
            "qr_png": "/Document/GetPaymentQr"
        },
        "docs": "Отправьте GET-запрос на любой endpoint, передав параметры сделки в query string."
    }


@app.route("/")
def index():
    return jsonify(_build_service_description())


@app.route("/docs")
def docs():
    return jsonify(_build_service_description())


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


@app.route("/Document/GetPdf")
def get_pdf():
    try:
        replacements, payment_details, qr_width_mm = prepare_generation_inputs()
        _, pdf_path, _ = build_doc(replacements, payment_details, qr_width_mm)
        return send_file(pdf_path, download_name="document.pdf", mimetype="application/pdf")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/Document/GetDocx")
def get_docx():
    try:
        replacements, payment_details, qr_width_mm = prepare_generation_inputs()
        docx_path, _, _ = build_doc(replacements, payment_details, qr_width_mm)
        return send_file(docx_path, download_name="document.docx", mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/Document/GetPdfZip")
def get_pdf_zip():
    try:
        replacements, payment_details, qr_width_mm = prepare_generation_inputs()
        _, pdf_path, _ = build_doc(replacements, payment_details, qr_width_mm)
        zip_buffer = zip_single_file(pdf_path, "document.pdf")
        return send_file(zip_buffer, download_name="document_pdf.zip", mimetype="application/zip", as_attachment=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/Document/GetDocxZip")
def get_docx_zip():
    try:
        replacements, payment_details, qr_width_mm = prepare_generation_inputs()
        docx_path, _, _ = build_doc(replacements, payment_details, qr_width_mm)
        zip_buffer = zip_single_file(docx_path, "document.docx")
        return send_file(zip_buffer, download_name="document_docx.zip", mimetype="application/zip", as_attachment=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/Document/GetAllZip")
def get_all_zip():
    try:
        replacements, payment_details, qr_width_mm = prepare_generation_inputs()
        docx_path, pdf_path, qr_path = build_doc(replacements, payment_details, qr_width_mm)
        file_mappings = [
            (docx_path, "document.docx"),
            (pdf_path, "document.pdf"),
            (qr_path, "payment_qr.png")
        ]
        zip_buffer = zip_files(file_mappings)
        return send_file(zip_buffer, download_name="documents_full.zip", mimetype="application/zip", as_attachment=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/Document/GetPaymentQr")
def get_payment_qr():
    try:
        replacements = get_replacements()
        payment_details = get_payment_details(request.args, replacements)
        try:
            qr_payload, qr_path = generate_payment_qr_image(payment_details, str(uuid.uuid4()))
        except RuntimeError as dependency_error:
            return jsonify({"error": str(dependency_error)}), 500

        if not qr_payload or not qr_path or not os.path.exists(qr_path):
            return jsonify({"error": "Не удалось сформировать QR-код"}), 400

        with open(qr_path, "rb") as qr_file:
            buffer = BytesIO(qr_file.read())
        buffer.seek(0)

        response = send_file(buffer, download_name="payment_qr.png", mimetype="image/png")
        response.headers["X-Payment-QR-Payload"] = qr_payload

        try:
            os.remove(qr_path)
        except OSError:
            pass

        return response
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=12345, threaded=False)
