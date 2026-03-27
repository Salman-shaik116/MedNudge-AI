from docx import Document
from PyPDF2 import PdfReader
from PIL import Image, ImageOps
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _extract_text_from_image(file):
    try:
        import pytesseract
    except ImportError as exc:
        raise ValueError(
            "OCR support requires 'pytesseract'. Install it (pip install pytesseract) and ensure the Tesseract engine is installed on the system."
        ) from exc

    try:
        file.seek(0)
    except Exception:
        pass

    try:
        image = Image.open(file)
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
    except Exception as exc:
        raise ValueError("Could not read the uploaded image file.") from exc

    try:
        tesseract_cmd = os.environ.get("TESSERACT_CMD")

        if not tesseract_cmd and os.name == "nt":
            candidates = [
                r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
            ]
            for candidate in candidates:
                if Path(candidate).exists():
                    tesseract_cmd = candidate
                    break

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        return pytesseract.image_to_string(image)
    except Exception as exc:
        raise ValueError(
            "Image OCR failed. Install the Tesseract OCR engine and make sure it is discoverable. "
            "On Windows you can install it via `winget install --id UB-Mannheim.TesseractOCR -e`, "
            "then restart the terminal/server. If it still isn't found, set `TESSERACT_CMD` (e.g. "
            "`C:\\Program Files\\Tesseract-OCR\\tesseract.exe`) in your `.env`."
        ) from exc

def extract_text(file):
    file_name = file.name.lower()

    # TEXT FILE
    if file_name.endswith(".txt"):
        return file.read().decode("utf-8")

    # DOCX FILE
    elif file_name.endswith(".docx"):
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])

    # PDF FILE
    elif file_name.endswith(".pdf"):
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text() or ""
            text += extracted + "\n"
        return text

    # IMAGE FILES (OCR)
    elif file_name.endswith((".png", ".jpg", ".jpeg")):
        return _extract_text_from_image(file)

    else:
        raise ValueError("File not supported")
