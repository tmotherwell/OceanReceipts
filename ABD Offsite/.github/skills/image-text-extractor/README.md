image-text-extractor skill

This skill reads receipt images from `input/`, runs OCR (Google Vision by default), and writes canonical JSON files to `output/`.

Quick start

1. (Optional) Create a virtualenv and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Place receipt images in the `input/` folder.
	- You can also place PDF receipts; each PDF file is treated as a single receipt (pages are concatenated).
4. Run the extractor:

```bash
python run_extractor.py
```

Notes
- The runner uses Google Cloud Vision by default. Provide credentials by setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to a service account JSON key, or enable Application Default Credentials.
- To use a different provider, set `OCR_PROVIDER` (e.g., `OCR_PROVIDER=tesseract`).
- Output JSON keys: `merchant`, `transaction_date` (ISO `YYYY-MM-DD`), `total` (numeric float).
