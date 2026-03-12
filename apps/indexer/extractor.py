"""
Text extraction module.

Dispatches on the file_type of an UploadedFile instance and returns raw
extracted text as a Python string.  Returns an empty string for types where
extraction is not supported (e.g. images without Tesseract installed).
"""

import logging

logger = logging.getLogger(__name__)


def extract_text(uploaded_file) -> str:
    """
    Extract plain text from an UploadedFile.

    Supports:
      - pdf   → PyPDF2
      - docx  → python-docx
      - md    → plain read (UTF-8)
      - png / jpg → pytesseract OCR (Tesseract must be installed on the host)

    Returns an empty string if the file type is unsupported or if extraction
    fails for any reason (errors are logged, never raised).
    """
    file_type = uploaded_file.file_type
    file_path = uploaded_file.file.path

    try:
        if file_type == 'pdf':
            return _extract_pdf(file_path)
        elif file_type == 'docx':
            return _extract_docx(file_path)
        elif file_type == 'md':
            return _extract_text_file(file_path)
        elif file_type in ('png', 'jpg'):
            return _extract_image(file_path)
        else:
            logger.warning('Unsupported file type for extraction: %s', file_type)
            return ''
    except Exception as exc:
        logger.error(
            'Text extraction failed for file id=%s type=%s: %s',
            uploaded_file.id, file_type, exc, exc_info=True,
        )
        return ''


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_pdf(file_path: str) -> str:
    import PyPDF2

    text_parts = []
    with open(file_path, 'rb') as fh:
        reader = PyPDF2.PdfReader(fh)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return '\n'.join(text_parts)


def _extract_docx(file_path: str) -> str:
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return '\n'.join(paragraphs)


def _extract_text_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read()


def _extract_image(file_path: str) -> str:
    """
    OCR-based text extraction for PNG/JPG images using pytesseract + Pillow.

    Requires the Tesseract binary to be installed on the host:
      - Debian/Ubuntu: apt install tesseract-ocr
      - Fedora:        dnf install tesseract
      - Docker:        add RUN apt-get install -y tesseract-ocr to Dockerfile

    If Tesseract is not available, logs a warning and returns empty string.
    """
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text or ''
    except pytesseract.pytesseract.TesseractNotFoundError:
        logger.warning(
            'Tesseract not found — skipping OCR for image %s. '
            'Install tesseract-ocr to enable image indexing.',
            file_path,
        )
        return ''
        logger.warning(
            'Tesseract not found — skipping OCR for image %s. '
            'Install tesseract-ocr to enable image indexing.',
            file_path,
        )
        return ''

