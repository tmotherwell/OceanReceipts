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


# Overrides removed: this runner no longer supports per-file manual overrides.


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
    s = re.sub(r'[^A-Za-z0-9 &]', ' ', s)
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


# load known merchants (optional helper list to improve normalization)
MERCHANTS = load_merchants(Path(__file__).resolve().parent)


def parse_merchant(lines: List[str]) -> Optional[str]:
    # Consider single lines and merged top-line spans (1-3 lines) as candidates.
    ignore_tokens = re.compile(r'\b(receipt|subtotal|tax|invoice|change|order|qty|unit|price|visa|mastercard|card)\b', re.I)
    merchant_keyword = re.compile(r'\b(restaurant|cafe|shop|store|market|bakery|bar|hotel|inn|bank|atm|scotiabank|aramark)\b', re.I)
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
    keyword = re.compile(r'\b(total|amount due|amount|grand total|balance due|paid|applied payment|applied payments|total due)\b', re.I)

    # currency-aware regex (includes common prefixes like CA$)
    currency_regex = re.compile(r'(?:CA\$|USD|EUR|GBP|AUD|CAD|[\$€£])\s*[-+]?\d[\d,]*(?:\.\d{2})?', re.I)

    candidates: List[Tuple[float, float]] = []  # (amount, score)

    for idx, line in enumerate(lines):
        if keyword.search(line):
            # scan the current line and a small window of following lines for amounts
            for j in range(idx, min(len(lines), idx + 3)):
                l = lines[j]
                # 1) currency-labeled amounts (strong signal)
                for m in re.findall(currency_regex, l):
                    val = normalize_amount_string(m)
                    if val is None:
                        continue
                    has_decimal = '.' in m or (',' in m and len(m.split(',')[-1]) == 2)
                    # stronger weighting for explicit currency and decimal-formatted amounts
                    score = (100.0) + (50.0 if has_decimal else 0.0) + (abs(val) / 1000.0)
                    candidates.append((val, score))
                # 2) explicit two-decimal tokens
                for t in find_two_decimal_amounts(l):
                    # prefer two-decimal tokens even if currency symbol is missing
                    score = 50.0 + (abs(t) / 1000.0)
                    candidates.append((t, score))
                # 3) any numeric tokens (filter obvious date-like tokens)
                for a in find_amounts(l):
                    # skip numbers that are almost certainly date components (e.g., 01/29/2026)
                    if ('/' in l or '-' in l) and re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', l) and abs(a) < 100:
                        continue
                    score = abs(a) / 1000.0
                    candidates.append((a, score))

    # If we found candidates near keyword lines, pick the best by score (currency & decimals prioritized)
    if candidates:
        best = max(candidates, key=lambda x: (x[1], abs(x[0])))
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


def process_file(image_path: Path, output_dir: Path) -> Path:
    result = {"merchant": None, "transaction_date": None, "total": None}
    header_text = ""
    is_pdf = image_path.suffix.lower() == ".pdf"

    try:
        if is_pdf:
            text, header_text = process_pdf(image_path)
        else:
            text, _ = ocr_image(image_path)
    except Exception as e:
        result["__error"] = f"OCR failed: {e}"
        # ... existing error handling ...
        return output_dir / f"{image_path.stem}_ocr.json"

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

    out_path = output_dir / f"{image_path.stem}_ocr.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return out_path


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    root = Path(__file__).resolve().parent
    input_dir = root / "input"
    output_dir = root / "output"
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    imgs = list(find_images(input_dir))
    if not imgs:
        logging.info("No images found in input/ — put receipt images there and re-run.")
        return
    for img in imgs:
        logging.info(f"Processing {img.name}")
        out = process_file(img, output_dir)
        logging.info(f"Wrote {out}")


if __name__ == "__main__":
    main()
