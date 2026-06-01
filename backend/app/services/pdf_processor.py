"""
PDF Processing Service
Handles text extraction from PDFs using pdfplumber for text PDFs
and OCR (Tesseract + EasyOCR fallback) for scanned image PDFs.
"""

import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.text_extractor import extract_multiple_records, has_bengali_content

logger = logging.getLogger(__name__)


# ─── PDF Text Extraction ──────────────────────────────────────────────────────

def extract_text_pdfplumber(pdf_path: str) -> Tuple[List[str], bool]:
    """
    Extract text from a text-based PDF using pdfplumber.
    
    Returns:
        (list of page texts, is_scanned_flag)
        is_scanned = True if pages returned empty/minimal text
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed. Run: pip install pdfplumber")
        return [], True

    pages_text = []
    empty_pages = 0

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                # Try table extraction as fallback for structured PDFs
                if not text.strip():
                    tables = page.extract_tables()
                    if tables:
                        table_text = []
                        for table in tables:
                            for row in table:
                                if row:
                                    table_text.append(" ".join(str(cell or "") for cell in row))
                        text = "\n".join(table_text)

                if not text.strip():
                    empty_pages += 1

                pages_text.append(text)

    except Exception as e:
        logger.error(f"pdfplumber failed on {pdf_path}: {e}")
        return [], True

    # Heuristic: if >50% pages are empty, likely scanned
    total_pages = len(pages_text)
    is_scanned = total_pages > 0 and (empty_pages / total_pages) > 0.5
    return pages_text, is_scanned


def extract_text_pymupdf(pdf_path: str) -> Tuple[List[str], bool]:
    """
    Extract text using PyMuPDF (fitz) as an alternative to pdfplumber.
    Often better for complex PDF layouts.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed. Run: pip install PyMuPDF")
        return [], True

    pages_text = []
    empty_pages = 0

    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text("text")
            if not text.strip():
                empty_pages += 1
            pages_text.append(text)
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF failed on {pdf_path}: {e}")
        return [], True

    total_pages = len(pages_text)
    is_scanned = total_pages > 0 and (empty_pages / total_pages) > 0.5
    return pages_text, is_scanned


# ─── OCR Extraction ───────────────────────────────────────────────────────────

def ocr_with_tesseract(image) -> Tuple[str, float]:
    """
    Run Tesseract OCR on a PIL image.
    
    Returns:
        (extracted_text, confidence_score)
    """
    try:
        import pytesseract
    except ImportError:
        logger.warning("pytesseract not installed")
        return "", 0.0

    try:
        # Bengali + English OCR
        lang_string = "+".join(settings.OCR_LANGUAGES)
        custom_config = f"--oem 3 --psm 6 -l {lang_string}"

        text = pytesseract.image_to_string(image, config=custom_config)

        # Get confidence scores
        data = pytesseract.image_to_data(
            image,
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )
        confidences = [int(c) for c in data["conf"] if str(c).isdigit() and int(c) >= 0]
        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

        return text, avg_confidence

    except Exception as e:
        logger.error(f"Tesseract OCR error: {e}")
        return "", 0.0


def ocr_with_easyocr(image) -> Tuple[str, float]:
    """
    Run EasyOCR on a PIL image with Bengali + English support.
    Used as a fallback when Tesseract confidence is low.
    
    Returns:
        (extracted_text, confidence_score)
    """
    try:
        import easyocr
        import numpy as np
    except ImportError:
        logger.warning("easyocr or numpy not installed")
        return "", 0.0

    try:
        # Initialize reader (cached per process)
        if not hasattr(ocr_with_easyocr, "_reader"):
            ocr_with_easyocr._reader = easyocr.Reader(
                ["bn", "en"],
                gpu=settings.EASYOCR_GPU,
                verbose=False,
            )

        reader = ocr_with_easyocr._reader
        img_array = np.array(image)
        results = reader.readtext(img_array, detail=1, paragraph=False)

        lines = []
        confidences = []
        for _bbox, text, confidence in results:
            lines.append(text)
            confidences.append(confidence)

        combined_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return combined_text, avg_confidence

    except Exception as e:
        logger.error(f"EasyOCR error: {e}")
        return "", 0.0


def pdf_page_to_image(pdf_path: str, page_number: int):
    """
    Convert a single PDF page to a PIL Image for OCR processing.
    Uses pdf2image (pdftoppm) for high-quality conversion.
    """
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(
            pdf_path,
            dpi=settings.PDF_DPI,
            first_page=page_number + 1,
            last_page=page_number + 1,
        )
        if images:
            return images[0]
    except Exception as e:
        logger.warning(f"pdf2image failed for page {page_number}: {e}")

    # Fallback: use PyMuPDF to render the page
    try:
        import fitz
        from PIL import Image
        import io

        doc = fitz.open(pdf_path)
        page = doc[page_number]
        mat = fitz.Matrix(settings.PDF_DPI / 72, settings.PDF_DPI / 72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        doc.close()
        return Image.open(io.BytesIO(img_data))
    except Exception as e:
        logger.error(f"PyMuPDF render failed for page {page_number}: {e}")
        return None


def ocr_page(pdf_path: str, page_number: int) -> Tuple[str, float]:
    """
    OCR a single PDF page using Tesseract, falling back to EasyOCR if confidence is low.
    
    Returns:
        (text, confidence_score)
    """
    image = pdf_page_to_image(pdf_path, page_number)
    if image is None:
        return "", 0.0

    # Primary: Tesseract
    text, confidence = ocr_with_tesseract(image)

    # Fallback to EasyOCR if Tesseract confidence is below threshold
    if confidence < settings.OCR_CONFIDENCE_THRESHOLD:
        logger.info(f"Tesseract confidence {confidence:.2f} low on page {page_number}, trying EasyOCR")
        easy_text, easy_confidence = ocr_with_easyocr(image)
        if easy_confidence > confidence:
            text = easy_text
            confidence = easy_confidence

    return text, confidence


# ─── File Utilities ───────────────────────────────────────────────────────────

def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file for duplicate detection."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_pdf_page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except Exception:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


# ─── Main PDF Processor ───────────────────────────────────────────────────────

def process_pdf(pdf_path: str) -> Dict:
    """
    Full PDF processing pipeline:
    1. Try text extraction (pdfplumber → PyMuPDF)
    2. If scanned, run OCR per page
    3. Extract voter records from each page's text
    
    Returns:
        {
            "records": [...],          # List of extracted voter field dicts
            "page_count": int,
            "is_scanned": bool,
            "ocr_confidence": float,
            "processing_time_seconds": float,
            "error": str or None,
        }
    """
    start_time = time.time()
    result = {
        "records": [],
        "page_count": 0,
        "is_scanned": False,
        "ocr_confidence": None,
        "processing_time_seconds": 0.0,
        "error": None,
    }

    if not Path(pdf_path).exists():
        result["error"] = f"File not found: {pdf_path}"
        return result

    try:
        # ── Step 1: Text extraction ────────────────────────────────────────
        pages_text, is_scanned = extract_text_pdfplumber(pdf_path)
        result["page_count"] = len(pages_text)

        # Fallback to PyMuPDF if pdfplumber returned nothing
        if not pages_text:
            pages_text, is_scanned = extract_text_pymupdf(pdf_path)
            result["page_count"] = len(pages_text)

        result["is_scanned"] = is_scanned

        # ── Step 2: OCR for scanned pages ──────────────────────────────────
        ocr_confidences = []

        if is_scanned or not any(has_bengali_content(p) for p in pages_text):
            logger.info(f"Running OCR on scanned PDF: {pdf_path}")
            result["is_scanned"] = True
            page_count = result["page_count"] or get_pdf_page_count(pdf_path)
            result["page_count"] = page_count

            ocr_pages = []
            for page_num in range(page_count):
                ocr_text, confidence = ocr_page(pdf_path, page_num)
                ocr_pages.append(ocr_text)
                if confidence > 0:
                    ocr_confidences.append(confidence)

            pages_text = ocr_pages

        # ── Step 3: Extract voter records ──────────────────────────────────
        all_records = []
        for page_num, page_text in enumerate(pages_text):
            if not page_text.strip():
                continue
            records = extract_multiple_records(page_text)
            for record in records:
                record["page_number"] = page_num + 1
            all_records.extend(records)

        result["records"] = all_records
        result["ocr_confidence"] = (
            sum(ocr_confidences) / len(ocr_confidences)
            if ocr_confidences else None
        )

        logger.info(
            f"Processed {pdf_path}: {len(all_records)} records "
            f"from {result['page_count']} pages "
            f"({'OCR' if result['is_scanned'] else 'text'})"
        )

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error processing {pdf_path}: {e}", exc_info=True)

    result["processing_time_seconds"] = round(time.time() - start_time, 3)
    return result
