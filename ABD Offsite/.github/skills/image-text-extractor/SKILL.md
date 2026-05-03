---
name: image-text-extractor
description: "**WORKFLOW SKILL** — Extracts `merchant`, `transaction_date`, and `total` from receipt images placed in the skill `input/` folder using OCR; writes canonical JSON files to the skill `output/` folder."
---

# image-text-extractor

## Summary
A reusable skill that ingests a receipt image from the skill `input/` folder, runs OCR, applies heuristics to find the merchant name, transaction date, and total amount, normalizes those values, and writes a JSON file to the skill `output/` folder.

## Input / Output
- Input folder: `input/` (place one or more receipt images: `.jpg`, `.jpeg`, `.png`, `.pdf`)
- Output folder: `output/`
- Output JSON structure (required fields):
  - `merchant` — string
  - `transaction_date` — string (ISO 8601 date `YYYY-MM-DD` by default)
  - `total` — number (decimal; numeric amount; no currency symbol included)
- Output filename pattern: `<original-basename>_ocr.json` (e.g., `receipt_001_ocr.json`)

### Example output
```json
{
  "merchant": "Firehouse Subs",
  "transaction_date": "2026-04-28",
  "total": 12.34
}
```

## Workflow Steps
1. Pick target file(s) from `input/`.
2. (Optional) Preprocess image: de-skew, denoise, convert to grayscale, upscale if very small.
3. Run OCR (default: Google Vision). Configurable provider supported (see Implementation Notes).
4. Parse extracted text lines and apply heuristics:
   - Merchant: prefer top-most prominent text line; fallback to lines matching known merchant patterns.
   - Transaction date: prefer lines with date-like patterns (MM/DD/YYYY, YYYY-MM-DD, DD Mon YYYY, etc.). Normalize to ISO `YYYY-MM-DD`.
   - Total: search for labeled amounts near keywords `total`, `amount`, `balance`, `paid`; otherwise pick the largest valid monetary value. Normalize to numeric decimal.
5. Validate fields against quality checks (see below).
6. Write canonical JSON to `output/<basename>_ocr.json`. If extraction fails, write JSON with missing fields set to `null` and include `__error` message in the file.

## Decision Points & Branching Logic
- Multiple dates found: choose the date nearest the total or the most recent date within a 14-day window of file modified time.
- Multiple monetary values: prefer values that appear with keywords (`Total`, `Amount Due`); if none, choose the largest positive value.
- Merchant detection: if top-most line is generic (e.g., `RECEIPT`), search for next prominent line or known merchant dictionary matches.
- If OCR confidence is low: optionally escalate to cloud OCR provider (if configured) or flag for manual review.

## Quality Criteria / Completion Checks
- `merchant` not empty string (preferred)
- `transaction_date` parses to a valid ISO date
- `total` is a positive number
- If any required field fails, output JSON must still be produced and include an explanatory `__error` field describing which value(s) could not be reliably extracted.

## Failure Modes & Troubleshooting
- Poor image quality → recommend better scan or enable higher-quality OCR provider.
- Multi-page PDFs → the runner treats each PDF file as a single receipt by concatenating text from all pages; if extraction from pages fails, consider improving scan quality or enabling OCR for each page.

## Implementation Notes (recommended)
- Default OCR: Tesseract via `pytesseract` or command-line `tesseract`.
- Optional cloud providers: Google Vision, Azure Computer Vision — enable via environment variables if preferred.
- Configurable environment variables:
  - `OCR_PROVIDER` (default: `tesseract`) — options: `tesseract`, `google_vision`, `azure`
    - `OCR_PROVIDER` (default: `google_vision`) — options: `google_vision`, `tesseract`, `azure`
    - `GOOGLE_APPLICATION_CREDENTIALS` — path to the Google Cloud service account JSON key file, or set via other ADC methods. Required when `OCR_PROVIDER=google_vision`.
  - `OCR_LANGS` — e.g., `eng` (comma-separated)
  - `OUTPUT_DATE_FORMAT` — default `YYYY-MM-DD`
  - `WRITE_CONFIDENCE` — `true|false` to include confidence metadata
-- Recommended libraries: `pillow`, `PyMuPDF` (for PDF rendering), `opencv-python`, `pytesseract` (optional for local OCR), `google-cloud-vision` (if using cloud OCR).

## Example Prompts / Usage
- Chat: "Run `image-text-extractor` on the files in the skill input folder and return the JSON outputs." 
- CLI/script: run your skill runner which scans `input/` and writes to `output/`.

## Defaults (resolved)
The skill is configured with the following defaults based on user preferences:
- **JSON keys**: snake_case (e.g. `transaction_date`).
- **`total`**: numeric (float), no currency symbol included.
- **Date format**: ISO `YYYY-MM-DD`.
- **Default OCR provider**: `google_vision` (requires Google Cloud credentials; override via env var `OCR_PROVIDER`).
- **Currency**: not included by default.

## Google Vision Notes
- The skill now uses Google Cloud Vision by default. Provide credentials via the `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to a service account JSON key, or use Application Default Credentials.
- When `OCR_PROVIDER=google_vision`, the runner calls the Vision API's `document_text_detection` to obtain OCR text.
- If credentials or network access are not available, the runner will write an output JSON with an `__error` explaining the failure.

## Checklist (before marking as done)
- [ ] Place test receipt image(s) in `input/`.
- [ ] Run extraction and verify `output/<basename>_ocr.json` contains `merchant`, `transaction_date`, and `total`.
- [ ] Confirm date and total normalization meets acceptance criteria.

## Next Steps / Extensions
- Add `currency_code` detection (ISO 4217) when helpful.
- Add merchant normalization via a merchant-name normalization table or external service.
- Add confidence scores per field in output JSON for downstream review.

---

If you want, I can now:
- implement a reference Python script that runs the skill using `pytesseract`, or
- change the JSON key naming to use spaces instead of underscores, or
- enable a cloud OCR provider and add instructions for credentials.
