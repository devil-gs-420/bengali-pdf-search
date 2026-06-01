"""
Bengali Text Extraction Engine
Parses extracted text from PDFs to identify and extract structured voter data fields.
Handles Bengali Unicode, mixed Bengali/English text, and various formatting patterns.
"""

import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ─── Bengali Unicode Ranges ───────────────────────────────────────────────────

BENGALI_RANGE = r"[\u0980-\u09FF]"
BENGALI_PATTERN = re.compile(BENGALI_RANGE)

# ─── Field Label Patterns ─────────────────────────────────────────────────────
# Maps Bengali/English field labels to their canonical field names.
# Multiple variants handle different OCR outputs and formatting styles.

FIELD_PATTERNS: Dict[str, List[re.Pattern]] = {
    "voter_id": [
        re.compile(r"(?:ভোটার\s*নম্বর|ভোটার\s*ক্রমিক|ভোটার\s*নং|Voter\s*(?:ID|No\.?|Number))[:\s।]+([^\n]+)", re.IGNORECASE),
        re.compile(r"(?:ক্রমিক|Serial)[:\s।]+(\d+)", re.IGNORECASE),
    ],
    "serial_number": [
        re.compile(r"(?:ক্রমিক\s*নম্বর|ক্রমিক\s*নং|Serial\s*(?:No\.?|Number))[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "name": [
        re.compile(r"(?:ভোটারের\s*নাম|নাম|Name)[:\s।]+([^\n]+)", re.IGNORECASE),
        re.compile(r"নাম\s*[:\s।]+(" + BENGALI_RANGE + r"[^\n]+)", re.IGNORECASE),
    ],
    "father_name": [
        re.compile(r"(?:পিতার\s*নাম|বাবার\s*নাম|পিতা|Father(?:'s)?\s*Name)[:\s।]+([^\n]+)", re.IGNORECASE),
        re.compile(r"পিতা[:\s।]+(" + BENGALI_RANGE + r"[^\n]+)", re.IGNORECASE),
    ],
    "mother_name": [
        re.compile(r"(?:মাতার\s*নাম|মায়ের\s*নাম|মাতা|Mother(?:'s)?\s*Name)[:\s।]+([^\n]+)", re.IGNORECASE),
        re.compile(r"মাতা[:\s।]+(" + BENGALI_RANGE + r"[^\n]+)", re.IGNORECASE),
    ],
    "spouse_name": [
        re.compile(r"(?:স্বামীর\s*নাম|স্ত্রীর\s*নাম|স্বামী\s*/\s*স্ত্রীর\s*নাম|Spouse(?:'s)?\s*Name)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "birth_date": [
        re.compile(r"(?:জন্ম\s*তারিখ|জন্মতারিখ|Date\s*of\s*Birth|D\.O\.B)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "gender": [
        re.compile(r"(?:লিঙ্গ|Gender|Sex)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "occupation": [
        re.compile(r"(?:পেশা|Occupation|Profession)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "address": [
        re.compile(r"(?:ঠিকানা|বাড়ি|Address|Residential\s*Address)[:\s।]+([^\n]+(?:\n[^\n]+)*?(?=\n[^\n]*:|\Z))", re.IGNORECASE),
    ],
    "village": [
        re.compile(r"(?:গ্রাম|মহল্লা|Village|Mohalla)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "post_office": [
        re.compile(r"(?:ডাকঘর|পোস্ট\s*অফিস|Post\s*Office)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "union_name": [
        re.compile(r"(?:ইউনিয়ন|ইউপি|Union|Union\s*Parishad)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "ward": [
        re.compile(r"(?:ওয়ার্ড|Ward\s*(?:No\.?|Number)?)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "upazila": [
        re.compile(r"(?:উপজেলা|থানা|Upazila|Upazilla|Thana)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "district": [
        re.compile(r"(?:জেলা|District)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
    "division": [
        re.compile(r"(?:বিভাগ|Division)[:\s।]+([^\n]+)", re.IGNORECASE),
    ],
}

# ─── District List (for validation/normalization) ─────────────────────────────

BANGLADESH_DISTRICTS = {
    "ঢাকা", "চট্টগ্রাম", "সিলেট", "রাজশাহী", "খুলনা", "বরিশাল", "রংপুর", "ময়মনসিংহ",
    "ফরিদপুর", "গাজীপুর", "নারায়ণগঞ্জ", "নরসিংদী", "মানিকগঞ্জ", "মুন্সিগঞ্জ",
    "কিশোরগঞ্জ", "টাঙ্গাইল", "জামালপুর", "শেরপুর", "নেত্রকোণা", "ময়মনসিংহ",
    "কুমিল্লা", "ব্রাহ্মণবাড়িয়া", "চাঁদপুর", "লক্ষ্মীপুর", "নোয়াখালী", "ফেনী",
    "খাগড়াছড়ি", "রাঙামাটি", "বান্দরবান", "কক্সবাজার",
    "Dhaka", "Chittagong", "Sylhet", "Rajshahi", "Khulna", "Barisal", "Rangpur",
    "Mymensingh", "Comilla", "Cox's Bazar",
}

# ─── Birth Year Extraction ────────────────────────────────────────────────────

BIRTH_YEAR_PATTERN = re.compile(r"\b(19[0-9]{2}|20[0-2][0-9])\b")
BENGALI_DIGIT_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize_bengali_digits(text: str) -> str:
    """Convert Bengali/Arabic-Indic digits to ASCII digits."""
    return text.translate(BENGALI_DIGIT_MAP)


def normalize_text(text: str) -> str:
    """
    Clean and normalize extracted text for pattern matching.
    - Normalize Unicode (NFC)
    - Remove excessive whitespace
    - Convert Bengali digits to ASCII for year/number extraction
    """
    if not text:
        return ""
    # Unicode normalization
    text = unicodedata.normalize("NFC", text)
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple spaces/tabs within lines
    text = re.sub(r"[ \t]+", " ", text)
    # Remove null bytes and control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def clean_field_value(value: str) -> str:
    """
    Clean a single extracted field value.
    Removes trailing punctuation, extra spaces, and artifacts.
    """
    if not value:
        return ""
    value = value.strip()
    # Remove trailing punctuation artifacts
    value = re.sub(r"[।,\.\s]+$", "", value)
    # Remove leading punctuation
    value = re.sub(r"^[।,\.\:\s]+", "", value)
    # Collapse internal whitespace
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_birth_year(birth_date_str: str) -> Optional[int]:
    """Extract a 4-digit birth year from a birth date string."""
    if not birth_date_str:
        return None
    # Convert Bengali digits first
    normalized = normalize_bengali_digits(birth_date_str)
    match = BIRTH_YEAR_PATTERN.search(normalized)
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2030:
            return year
    return None


def has_bengali_content(text: str) -> bool:
    """Return True if the text contains Bengali characters."""
    return bool(BENGALI_PATTERN.search(text))


# ─── Main Extraction Function ─────────────────────────────────────────────────

def extract_voter_fields(text: str) -> Dict[str, Optional[str]]:
    """
    Parse raw text extracted from a PDF page and extract structured voter data fields.
    
    Args:
        text: Raw text extracted from a PDF page (Bengali/English mixed).
    
    Returns:
        Dictionary of field names to extracted values (None if not found).
    """
    normalized = normalize_text(text)
    result: Dict[str, Optional[str]] = {field: None for field in FIELD_PATTERNS}

    for field_name, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(normalized)
            if match:
                value = clean_field_value(match.group(1))
                if value:
                    result[field_name] = value
                    break  # Use first matching pattern

    # Post-processing: extract birth year from birth_date
    if result.get("birth_date"):
        result["birth_year"] = str(extract_birth_year(result["birth_date"]) or "")
    else:
        result["birth_year"] = None

    return result


def extract_multiple_records(text: str) -> List[Dict[str, Optional[str]]]:
    """
    Some PDFs contain multiple voter records per page, separated by dividers or serial numbers.
    This function attempts to split the page text into individual records.
    
    Returns a list of field dictionaries (one per voter record found).
    """
    # Common record separators in Bangladesh voter lists
    separators = [
        r"(?=ভোটার\s*নম্বর\s*[:\s।])",        # Voter number marker
        r"(?=ক্রমিক\s*নম্বর\s*[:\s।]\s*\d)",  # Serial number marker
        r"(?=\n\s*\d+\s*।\s*\n)",              # Numbered list item
        r"─{3,}|={3,}|\*{3,}",                 # Horizontal dividers
    ]

    records = []
    segments = [text]

    # Try to split by the most reliable separator first
    for separator in separators:
        parts = re.split(separator, text)
        if len(parts) > 1:
            segments = [p.strip() for p in parts if p.strip()]
            break

    for segment in segments:
        if has_bengali_content(segment) and len(segment) > 20:
            fields = extract_voter_fields(segment)
            # Only include if we extracted at least one meaningful field
            meaningful = [v for v in fields.values() if v and len(str(v)) > 1]
            if len(meaningful) >= 1:
                fields["raw_text"] = segment[:2000]  # Store first 2000 chars for debugging
                records.append(fields)

    # If no segments found, try the whole text as a single record
    if not records and has_bengali_content(text):
        fields = extract_voter_fields(text)
        fields["raw_text"] = text[:2000]
        records.append(fields)

    return records


def calculate_extraction_confidence(fields: Dict[str, Optional[str]]) -> float:
    """
    Estimate extraction quality as a 0-1 confidence score.
    Higher score = more fields successfully extracted.
    """
    key_fields = ["name", "father_name", "voter_id", "district", "upazila"]
    secondary_fields = ["mother_name", "birth_date", "address", "union_name", "ward"]

    key_count = sum(1 for f in key_fields if fields.get(f))
    secondary_count = sum(1 for f in secondary_fields if fields.get(f))

    # Key fields weighted 2x
    score = (key_count * 2 + secondary_count) / (len(key_fields) * 2 + len(secondary_fields))
    return min(round(score, 3), 1.0)
