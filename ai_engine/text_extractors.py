from pathlib import Path
import fitz
from docx import Document as DocxDocument


def extract_text(file_path):
    suffix = Path(file_path).suffix.lower()
    if suffix == '.pdf':
        return extract_pdf(file_path)
    if suffix == '.docx':
        return extract_docx(file_path)
    if suffix == '.txt':
        return Path(file_path).read_text(encoding='utf-8', errors='ignore')
    raise ValueError('Unsupported file type')


def extract_pdf(file_path):
    text = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text.append(page.get_text())
    return '\n'.join(text).strip()


def extract_docx(file_path):
    doc = DocxDocument(file_path)
    return '\n'.join(p.text for p in doc.paragraphs).strip()
