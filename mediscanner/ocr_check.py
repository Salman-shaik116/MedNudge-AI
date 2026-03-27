"""Quick OCR self-check for local development.

Run:
  python manage.py shell -c "from mediscanner.ocr_check import run_check; run_check()"

Notes:
- Requires `pytesseract` Python package.
- Requires the Tesseract OCR engine installed on the machine.
"""

from __future__ import annotations

import os
from pathlib import Path


def _configure_tesseract_cmd(pytesseract_module) -> str | None:
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
        pytesseract_module.pytesseract.tesseract_cmd = tesseract_cmd
    return tesseract_cmd


def run_check() -> None:
    try:
        import pytesseract  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "pytesseract is not installed. Run: pip install pytesseract"
        ) from exc

    _configure_tesseract_cmd(pytesseract)

    try:
        version = pytesseract.get_tesseract_version()
    except Exception as exc:
        raise RuntimeError(
            "Tesseract OCR engine not found. Install Tesseract and ensure `tesseract` is on PATH."
        ) from exc

    print(f"Tesseract OK: {version}")
