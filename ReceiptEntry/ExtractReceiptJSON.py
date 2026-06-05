#!/usr/bin/env python3
"""
Improved Google Vision-based runner for the image-text-extractor skill.

Features added:
- Prefers two-decimal small amounts (e.g., 11.70) when selecting totals.
- Normalizes merchant text (strip non-letters, collapse spaces, title-case).
"""

import os
import re
import json
import logging
import difflib
from pathlib import Path
from typing import Optional, List, Tuple
import sys
import config

try:
    from google.cloud import vision
    from google.api_core.exceptions import GoogleAPIError
    from google.auth.exceptions import DefaultCredentialsError
except Exception:
    vision = None
    GoogleAPIError = None
    DefaultCredentialsError = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from dateutil.parser import parse as date_parse
except Exception:
    date_parse = None


def find_images(input_dir: Path):
    exts = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".pdf")
    for path in sorted(input_dir.iterdir()):
        if path.suffix.lower() in exts and path.is_file():
            yield path


def ocr_image_google(path: Path) -> Tuple[str, dict]:
    if vision is None:
        raise RuntimeError("google-cloud-vision is not installed; install with `pip install google-cloud-vision`")
    try:
        client = vision.ImageAnnotatorClient()
    except Exception as e:
        raise RuntimeError(f"Could not initialize Google Vision client: {e}")
    content = path.read_bytes()
    image = vision.Image(content=content)
    try:
        response = client.document_text_detection(image=image)
    except DefaultCredentialsError:
        raise RuntimeError("Google credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON key.")
    except Exception as e:
        raise RuntimeError(f"Google Vision API error: {e}")
    if getattr(response, "error", None) and getattr(response.error, "message", None):
        raise RuntimeError(f"Google Vision error: {response.error.message}")
    text = ""
    if getattr(response, 'full_text_annotation', None) and getattr(response.full_text_annotation, 'text', None):
        text = response.full_text_annotation.text
    elif getattr(response, 'text_annotations', None):
        text = response.text_annotations[0].description
    return text, {}


def ocr_image_bytes(content: bytes) -> Tuple[str, dict]:
    """Run Google Vision OCR on raw image bytes and return text."""
    if vision is None:
        raise RuntimeError("google-cloud-vision is not installed; install with `pip install google-cloud-vision`")
    try:
        client = vision.ImageAnnotatorClient()
    except Exception as e:
        raise RuntimeError(f"Could not initialize Google Vision client: {e}")
    image = vision.Image(content=content)
    try:
        response = client.document_text_detection(image=image)
    except DefaultCredentialsError:
        raise RuntimeError("Google credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON key.")
    except Exception as e:
        raise RuntimeError(f"Google Vision API error: {e}")
    if getattr(response, "error", None) and getattr(response.error, "message", None):
        raise RuntimeError(f"Google Vision error: {response.error.message}")
    text = ""
    if getattr(response, 'full_text_annotation', None) and getattr(response.full_text_annotation, 'text', None):
        text = response.full_text_annotation.text
    elif getattr(response, 'text_annotations', None):
        text = response.text_annotations[0].description
    return text, {}


def clean_pdf_text(text: str) -> Tuple[str, str]:
    """
    Returns a tuple of (cleaned_body, header_text).
    """
    if not text:
        return "", ""
    
    lines = text.splitlines()
    email_addr_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
    header_colon_pattern = re.compile(r'^\s*(From|Sent|To|Subject|Date|Cc|Bcc|Reply-To|Attachments)\s*:', re.I)
    forwarded_pattern = re.compile(r'forwarded message|original message', re.I)

    N = min(20, len(lines))
    header_like_count = 0
    end = 0
    
    for i in range(N):
        s = lines[i].strip()
        if not s: continue
        if header_colon_pattern.match(s) or email_addr_pattern.search(s) or forwarded_pattern.search(s):
            header_like_count += 1
            end = i + 1 # Keep track of the end of the header block

    header_text = "\n".join(lines[:end])
    body_lines = lines[end:]

    # Further clean the body as in the original script
    cleaned_body_lines = []
    footer_patterns = re.compile(r'^(Sent from my|If you have questions|To view this message|This message was sent)', re.I)
    for line in body_lines:
        s = line.strip()
        if not s or not (email_addr_pattern.search(s) or footer_patterns.match(s)):
            cleaned_body_lines.append(line)
            
    return "\n".join(cleaned_body_lines).strip(), header_text.strip()


def process_pdf(path: Path) -> Tuple[str, str]:
    """Extract text from PDF. Returns (cleaned_text, header_text)."""
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required.")
    doc = fitz.open(str(path))
    full_text = []
    for page in doc:
        page_text = page.get_text("text")
        if not (page_text and len(re.sub(r"\s+", "", page_text)) > 20):
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            page_text, _ = ocr_image_bytes(pix.tobytes("png"))
        full_text.append(page_text)
    
    raw = "\n".join(full_text)
    cleaned, header = clean_pdf_text(raw)
    return cleaned, header


def ocr_image(path: Path) -> Tuple[str, dict]:
    provider = os.environ.get("OCR_PROVIDER", "google_vision").lower()
    if provider == "google_vision":
        return ocr_image_google(path)
    raise RuntimeError(f"Unsupported OCR provider: {provider}")


def normalize_merchant(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    s = s.replace('[', ' ').replace(']', ' ').replace('?', ' ')
    # preserve hyphens in vendor names like 'Z-TECA'
    s = re.sub(r'[^A-Za-z0-9 &-]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.title()


def load_merchants(root: Path) -> List[str]:
    path = root / "merchants.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str)]
    except Exception:
        pass
    return []


def sanitize_filename_component(value: str, default: str) -> str:
    if not value:
        return default
    value = value.strip()
    value = re.sub(r'[^A-Za-z0-9 _-]', '_', value)
    value = re.sub(r'[\s_]+', '_', value).strip('_')
    return value or default


def find_known_merchant_from_lines(lines: List[str]) -> Optional[str]:
    if not MERCHANTS:
        return None
    cleaned_lines = [re.sub(r'[^a-z0-9 ]', ' ', line.lower()) for line in lines]
    for km in MERCHANTS:
        km_clean = re.sub(r'[^a-z0-9 ]', ' ', km.lower()).strip()
        if not km_clean:
            continue
        for line in cleaned_lines:
            if km_clean in line:
                return km
    return None


# load known merchants (optional helper list to improve normalization)
MERCHANTS = load_merchants(Path(__file__).resolve().parent)


def parse_merchant(lines: List[str]) -> Optional[str]:
    # Consider single lines and merged top-line spans (1-3 lines) as candidates.
    ignore_tokens = re.compile(
        r'\b(receipt|subtotal|tax|invoice|change|order|qty|unit|price|visa|mastercard|card|total|balance|amount|due|paid|payment|payments|fee|fees|surcharge|surcharges|trip|fare|insurance|support|privacy|terms|download|contact|purchase|transaction|record|username|approved|signature|retain|important|entry|ref#|auth#)\b',
        re.I,
    )
    merchant_keyword = re.compile(r'\b(restaurant|cafe|shop|store|market|bakery|bar|hotel|inn|bank|atm|scotiabank|aramark)\b', re.I)
    if MERCHANTS:
        known = find_known_merchant_from_lines(lines)
        if known:
            return known

    def is_potential_merchant(line: str) -> bool:
        if ignore_tokens.search(line):
            return False
        core = re.sub(r'[^A-Za-z ]', '', line)
        if len(core) < 3:
            return False
        words = [w for w in line.split() if re.search(r'[A-Za-z]', w)]
        return len(words) >= 2 and len(re.sub(r'[^A-Za-z]', '', ' '.join(words))) >= 4

    for ln in lines[:8]:
        if not ln or not ln.strip():
            continue
        candidate = ln.strip()
        if is_potential_merchant(candidate):
            return normalize_merchant(candidate)

    # Quick heuristic: prefer the first non-empty line if it looks like a merchant.
    first_line = None
    for ln in lines:
        if ln and ln.strip():
            first_line = ln.strip()
            break
    if first_line:
        # treat as merchant if not an obvious generic token
        if is_potential_merchant(first_line):
            return normalize_merchant(first_line)

    candidates = []
    max_lines = min(6, len(lines))
    for i in range(max_lines):
        for span in (1, 2, 3):
            chunk = ' '.join(lines[i:i+span]).strip()
            if not chunk:
                continue
            if len(chunk) < 2:
                continue
            if ignore_tokens.search(chunk):
                continue
            letters = sum(1 for c in chunk if c.isalpha())
            digits = sum(1 for c in chunk if c.isdigit())
            alpha_ratio = letters / max(1, len(chunk))
            digit_ratio = digits / max(1, len(chunk))
            uppercase_letters = sum(1 for c in chunk if c.isupper())
            uppercase_ratio = uppercase_letters / max(1, letters) if letters else 0
            score = 0.0
            # prefer top positions
            score += max(0, (10 - i)) * 0.5
            # prefer alphabetic content
            score += alpha_ratio * 5.0
            # penalize digit-heavy lines
            score -= digit_ratio * 5.0
            # uppercase emphasis
            if uppercase_ratio > 0.6:
                score += 1.0
            # merchant keywords boost
            if merchant_keyword.search(chunk):
                score += 6.0
            # word count preference
            wc = len(chunk.split())
            if 1 <= wc <= 5:
                score += 1.0
            candidates.append((score, chunk, i))

    if not candidates:
        return None
    # pick best scoring candidate; tie-breaker: earliest appearance
    candidates.sort(key=lambda x: (-x[0], x[2]))
    best = candidates[0][1]
    best_norm = normalize_merchant(best)

    # fuzzy-match against known merchants if available
    if MERCHANTS:
        match = difflib.get_close_matches(best_norm, MERCHANTS, n=1, cutoff=0.6)
        if match:
            return match[0]
        # if any known merchant token appears in the chunk, prefer that known merchant
        chunk_clean = re.sub(r'[^a-z0-9\s]', '', best_norm.lower())
        for km in MERCHANTS:
            km_clean = re.sub(r'[^a-z0-9\s]', '', km.lower())
            for token in km_clean.split():
                if token and token in chunk_clean:
                    return km

    return best_norm


def normalize_amount_string(s: str) -> Optional[float]:
    if not s:
        return None
    s = re.sub(r'[A-Za-z\$€£\s]', '', s)
    s = re.sub(r'[^0-9,\.\-]', '', s)
    if not s:
        return None
    try:
        if s.count('.') and s.count(','):
            # decide which is decimal by position of last separator
            if s.rfind('.') > s.rfind(','):
                s = s.replace(',', '')
            else:
                s = s.replace('.', '').replace(',', '.')
        elif s.count(','):
            if len(s.split(',')[-1]) == 2:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        elif s.count('.'):
            if len(s.split('.')[-1]) != 2:
                s = s.replace('.', '')
        return float(s)
    except Exception:
        return None


def find_amounts(text: str) -> List[float]:
    token_pattern = r'(?:(?:USD|EUR|GBP|AUD|CAD|[\$€£])\s*)?[-+]?\d[\d\.,\s]*\d'
    matches = re.findall(token_pattern, text)
    amounts = []
    for m in matches:
        val = normalize_amount_string(m)
        if val is not None:
            amounts.append(val)
    return amounts


def find_two_decimal_amounts(text: str) -> List[float]:
    # tokens that explicitly have exactly two digits after final separator
    pattern = r'(?:(?:USD|EUR|GBP|AUD|CAD|[\$€£])\s*)?[-+]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})'
    matches = re.findall(pattern, text)
    amounts = []
    for m in matches:
        val = normalize_amount_string(m)
        if val is not None:
            amounts.append(val)
    return amounts


def find_amounts_near_phrases(text: str, phrases: List[str] = None, line_window: int = 2) -> List[float]:
    """Search text for occurrences of any phrase and return amounts found within nearby lines.

    Prefers explicit currency tokens first, then two-decimal tokens, then any numeric tokens.
    """
    if phrases is None:
        phrases = [
            "applied payments",
            "applied payment",
            "payments applied",
            "payment applied",
            "applied payment(s)",
        ]
    lines = text.splitlines()
    found: List[float] = []
    # currency-aware regex: $/€/£ or 3-letter codes followed by amount with two decimals
    currency_regex = r"[\$€£]\s*[-+]?\d[\d,]*(?:\.\d{2})|\b(?:USD|EUR|GBP|CAD|AUD)\s*[-+]?\d[\d,]*(?:\.\d{2})\b"
    for idx, line in enumerate(lines):
        low = line.lower()
        for ph in phrases:
            if ph in low:
                start = max(0, idx - line_window)
                end = min(len(lines), idx + line_window + 1)
                window_text = "\n".join(lines[start:end])
                # 1) currency-symbol or code matches
                currency_matches = re.findall(currency_regex, window_text)
                for m in currency_matches:
                    v = normalize_amount_string(m)
                    if v is not None:
                        found.append(v)
                if found:
                    continue
                # 2) explicit two-decimal tokens
                two = find_two_decimal_amounts(window_text)
                if two:
                    found.extend(two)
                    continue
                # 3) any numeric candidates
                any_amt = find_amounts(window_text)
                if any_amt:
                    found.extend(any_amt)
    return found


def parse_date(text: str) -> Optional[str]:
    # Expanded month and weekday regex
    months = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)'
    weekdays = r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
    
    patterns = [
        # New pattern for: Tue, Jan 6, 2026
        rf'{weekdays},\s+{months}\s+\d{{1,2}},\s+\d{{4}}', 
        r'\d{4}-\d{2}-\d{2}',
        # pattern for hyphenated month names like 22-May-2026
        rf'\d{{1,2}}-{months}-\d{{2,4}}',
        r'\d{1,2}/\d{1,2}/\d{2,4}',
        r'\d{1,2}-\d{1,2}-\d{2,4}',
        r'\d{1,2}\.\d{1,2}\.\d{2,4}',
        rf'\d{{1,2}}\s+{months}\s+\d{{2,4}}',
        rf'{months}\s+\d{{1,2}},?\s*\d{{2,4}}',
    ]
    
    for p in patterns:
        matches = re.findall(p, text, re.I)
        for m in matches:
            if date_parse:
                try:
                    # dateutil handles the weekday component automatically
                    dt = date_parse(m, fuzzy=True, dayfirst=False)
                    return dt.date().isoformat()
                except Exception:
                    continue
    # fallback: try any date-like substring with dateutil
    if date_parse:
        try:
            dt = date_parse(text, fuzzy=True, dayfirst=False)
            return dt.date().isoformat()
        except Exception:
            pass
    return None


def parse_total(text: str) -> Optional[float]:
    lines = text.splitlines()
    # currency-aware regex (includes common prefixes like CA$)
    currency_regex = re.compile(r'(?:CA\$|USD|EUR|GBP|AUD|CAD|[\$€£])\s*[-+]?\d[\d,]*(?:\.\d{2})?', re.I)

    def find_amount_after_phrases(phrases: List[str], line_window: int = 12) -> Optional[float]:
        for idx, line in enumerate(lines):
            low = line.lower()
            for ph in phrases:
                if ph in low:
                    candidates: List[float] = []
                    for j in range(idx, min(len(lines), idx + line_window + 1)):
                        l = lines[j]
                        for m in re.findall(currency_regex, l):
                            val = normalize_amount_string(m)
                            if val is not None and val > 0:
                                candidates.append(val)
                        two = find_two_decimal_amounts(l)
                        for val in two:
                            if val > 0:
                                candidates.append(val)
                        if re.search(r'[\$€£]', l) or re.search(r'\d[.,]\d{2}\b', l):
                            plain = [a for a in find_amounts(l) if a > 0]
                            candidates.extend(plain)
                        if re.search(r'\b(tip|suggestion|thank you|please come again|tips|tips suggestions|gratuity)\b', l, re.I):
                            break
                    if candidates:
                        if ph in ('final total', 'grand total'):
                            return round(candidates[0], 2)
                        return round(candidates[-1], 2)
        return None

    total_due = find_amount_after_phrases(['total due', 'amount due', 'balance due', 'final total', 'grand total'], line_window=12)
    if total_due is not None:
        return total_due

    keyword = re.compile(r'\b(total|amount due|amount|grand total|balance due|paid|applied payment|applied payments|total due)\b', re.I)

    def is_discount_context(line: str) -> bool:
        return bool(re.search(r'\b(discount|pre-discount|promo|savings|off|deduct|refund|adjustment|subtotal)\b', line, re.I))

    for idx, line in enumerate(lines):
        if keyword.search(line):
            if is_discount_context(line):
                # ignore lines like 'Discount Total' and standalone 'Subtotal' when searching for the final total
                continue
            nearby: List[Tuple[int, float, str, bool, bool]] = []
            for j in range(idx, min(len(lines), idx + 6)):
                l = lines[j]
                for m in re.findall(currency_regex, l):
                    val = normalize_amount_string(m)
                    if val is None:
                        continue
                    nearby.append((j - idx, val, l, True, True))
                for t in find_two_decimal_amounts(l):
                    nearby.append((j - idx, t, l, False, True))
                line_has_currency = bool(re.search(r'(?:USD|EUR|GBP|AUD|CAD|[\$€£])', l, re.I))
                line_is_total_related = bool(re.search(r'\b(total|amount|balance|due|charge|subtotal|grand total)\b', l, re.I))
                for a in find_amounts(l):
                    if ('/' in l or '-' in l) and re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', l) and abs(a) < 100:
                        continue
                    if re.search(r'\b(card|mastercard|visa|amex|auth|reference|mid|transaction)\b', l, re.I) and (100 <= abs(a) <= 10000):
                        continue
                    if not line_has_currency and not line_is_total_related:
                        if not re.search(r'\d[.,]\d{2}\b', l):
                            continue
                        if len(re.findall(r'\d+', l)) > 1:
                            continue
                    nearby.append((j - idx, a, l, False, False))

            def total_summary_context(index: int) -> bool:
                context_range = lines[max(0, index - 3):index]
                context_text = "\n".join(context_range)
                return bool(re.search(r'\b(subtotal|hst|gst|pst|qst|tax|discount)\b', context_text, re.I))

            currency_candidates = [val for pos, val, l, is_curr, is_two in nearby if val > 0 and is_curr and not is_discount_context(l)]
            if currency_candidates:
                if total_summary_context(idx):
                    return round(currency_candidates[-1], 2)
                return round(currency_candidates[0], 2)

            two_dec_candidates = [val for pos, val, l, is_curr, is_two in nearby if val > 0 and is_two and not is_discount_context(l)]
            if two_dec_candidates:
                if total_summary_context(idx):
                    return round(two_dec_candidates[-1], 2)
                return round(two_dec_candidates[0], 2)

            candidates: List[Tuple[float, float]] = []
            for pos, val, l, is_curr, is_two in nearby:
                if val is None or val <= 0:
                    continue
                score = 0.0
                if is_curr:
                    score += 50.0
                if is_two:
                    score += 30.0
                score += max(0.0, (10 - pos)) * 2.0
                if val < 100:
                    score += 5.0
                elif val < 1000:
                    score += 2.0
                if val > 10000:
                    score -= 20.0
                if not is_discount_context(l):
                    score += 5.0
                if re.search(r'\b(total|amount|balance|due|charge|subtotal|grand total)\b', l, re.I):
                    score += 8.0
                candidates.append((val, score, l))
            if candidates:
                best = max(candidates, key=lambda x: (x[1], -abs(x[0])))
                return round(abs(best[0]), 2)

    # Fallbacks: prefer explicit two-decimal tokens anywhere in the text
    two = find_two_decimal_amounts(text)
    two_small = [c for c in two if 0 < abs(c) <= 100000]
    if two_small:
        return round(max(two_small), 2)

    # Final fallback: any numeric token, excluding obvious date fragments
    all_amounts = find_amounts(text)
    filtered = []
    for m in all_amounts:
        if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text) and abs(m) < 100:
            continue
        filtered.append(m)
    if filtered:
        return round(max(filtered), 2)

    return None

def get_unique_path(target_path: Path) -> Path:
    """
    Checks if a file exists. If it does, appends an incrementing counter 
    (e.g., filename_1.json, filename_2.json) until a free path is found.
    """
    if not target_path.exists():
        return target_path
        
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    counter = 1
    
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1

def send_file_for_OCR(image_path: Path) -> Tuple[str,str]:
    header_text = ""
    is_pdf = image_path.suffix.lower() == ".pdf"

    try:
        if is_pdf:
            text, header_text = process_pdf(image_path)
        else:
            text, _ = ocr_image(image_path)
        return text, header_text
    except Exception as e:
       logging.error(f"OCR failed for {image_path.name}: {e}")
       return None

def process_returned_OCR(text: str, header_text: str, image_path: Path):
    result = {"merchant": None, "transaction_date": None, "total": None}
    # 1. Primary Extraction from cleaned text
    lines = [l for l in text.splitlines() if l.strip()]
    result["merchant"] = parse_merchant(lines)
    result["transaction_date"] = parse_date(text)
    
# 2. TARGETED FALLBACK FOR EMAIL HEADERS[cite: 1]
    # If PDF and date is missing, or it's clearly an email layout
    if image_path.suffix.lower() == ".pdf" and (not result["transaction_date"] or header_text):
        
        # Priority 1: Look for the specific "Tue, Jan 6, 2026" format in the header[cite: 1]
        header_date = parse_date(header_text)
        if header_date:
            result["transaction_date"] = header_date
            
        # Priority 2: If date is still missing, look for common email Date lines[cite: 1]
        if not result["transaction_date"]:
            date_line_match = re.search(r'Date:\s*(.*)', header_text, re.I)
            if date_line_match:
                result["transaction_date"] = parse_date(date_line_match.group(1))
        
        # Optionally: If merchant is still missing, try looking in header
        if not result["merchant"] and header_text:
            # Simple fallback: look for common 'From: Merchant Name' pattern
            from_match = re.search(r'From:\s*(.*)', header_text, re.I)
            if from_match:
                result["merchant"] = normalize_merchant(from_match.group(1))
    
    
    # result["transaction_date"] = parse_date(text)
    raw_total = parse_total(text)
    if raw_total is not None:
        # numeric total rounded to two decimals
        try:
            result["total"] = round(float(raw_total), 2)
            # also include a string with exactly two decimal places
            result["total_formatted"] = f"{result['total']:.2f}"
        except Exception:
            result["total"] = None

    missing = []
    if not result["merchant"]:
        missing.append("merchant")
    if not result["transaction_date"]:
        missing.append("transaction_date")
    if result["total"] is None:
        missing.append("total")
    if missing:
        result["__error"] = f"Could not reliably extract: {', '.join(missing)}"

    return result

def process_file(image_path: Path, output_dir: Path) -> Tuple[Path, Path]:
    result = {"merchant": None, "transaction_date": None, "total": None}
    text, header_text = send_file_for_OCR(image_path)
    if text is None:
            return None,None
    # output raw OCR output for debugging purposes
    if config.debug_SaveReturnedOCR:
        raw_ocr_path = output_dir / f"{image_path.stem}.txt"
        raw_header_path = output_dir / f"{image_path.stem}.head"
        raw_ocr_path.write_text(text, encoding="utf-8")
        raw_header_path.write_text(header_text, encoding="utf-8")

    result = process_returned_OCR(text, header_text, image_path)

    out_path = output_dir / f"{image_path.stem}_ocr.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    date_part = sanitize_filename_component(result.get("transaction_date"), "dateUnknown")
    merchant_part = sanitize_filename_component(result.get("merchant"), "merchantUnknown")
    new_stem = f"{date_part}_{merchant_part}"

    proposed_out_path = out_path.with_name(f"{new_stem}{out_path.suffix}")
    final_out_path = get_unique_path(proposed_out_path)

    # 2. Resolve unique path for the Input Image file
    proposed_input_path = image_path.with_name(f"{new_stem}{image_path.suffix}")
    final_input_path = get_unique_path(proposed_input_path)

    # Rename JSON file if the final path differs from the initial temporary one
    if final_out_path != out_path:
        out_path = out_path.rename(final_out_path)
    else:
        out_path = final_out_path

    # Rename Input Image file if the final path differs from its original location
    if final_input_path != image_path:
        image_path = image_path.rename(final_input_path)
    else:
        image_path = final_input_path

    logging.info(f"Extracted merchant: {result['merchant']}, date: {result['transaction_date']}, total: {result.get('total_formatted', 'None')}")
    return out_path, image_path


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    root = Path(__file__).resolve().parent
    input_dir = root / config.receiptInputDir
    output_dir = root / config.jsonDir
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    imgs = list(find_images(input_dir))
    if not imgs:
        logging.info("No images found in input/ — put receipt images there and re-run.")
        return
    output_mapping = {}
    for img in imgs:
        # logging.info(f"Processing {img.name}")
        out_path, renamed_input_path = process_file(img, output_dir)
        if out_path and renamed_input_path:
            output_mapping[str(out_path)] = str(renamed_input_path)
    
    while True:
        continueDecision = input("Continue to receipt entry? (y/n)")
        if continueDecision == "y":
            return output_mapping
        elif continueDecision == "n":
            print("Exiting")
            sys.exit(0)
        else:
            print("Invalid input")

if __name__ == "__main__":
    main()
