from docx import Document
from PyPDF2 import PdfReader

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
            text += page.extract_text() + "\n"
        return text

    else:
        raise ValueError("File not supported")
