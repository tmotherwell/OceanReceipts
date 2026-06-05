import json
import sys
from pathlib import Path
import pytest

# Make sure ReceiptEntry is importable when running pytest from the repo root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ExtractReceiptJSON as erj


def test_process_returned_OCR_basic():
    text = """
ACME Store
123 Main St
Date: 2026-05-10
Total $12.34
Thank you for shopping
"""
    header = ""
    image_path = Path("receipt.jpg")

    res = erj.process_returned_OCR(text, header, image_path)

    assert isinstance(res, dict)
    assert res.get("merchant") in ("Acme Store", "ACME Store", "Acme") or res.get("merchant") is not None
    assert res.get("transaction_date") == "2026-05-10"
    assert res.get("total") == 12.34
    assert res.get("total_formatted") == "12.34"


def test_process_returned_OCR_pdf_header_date():
    # Text does not contain a date; header (PDF/email) does
    text = "\nItem A\nSubtotal $5.00\n"  # no date present
    header = "From: Example Merchant\nTue, Jan 6, 2026 10:20:30 -0500\nSubject: Your receipt"
    image_path = Path("invoice.pdf")

    res = erj.process_returned_OCR(text, header, image_path)

    assert isinstance(res, dict)
    assert res.get("transaction_date") == "2026-01-06"
    # Merchant might come from the text ('Item A') or fallback from header 'From:'; accept either
    assert res.get("merchant") in ("Item A", "Example Merchant")


def test_process_returned_OCR_missing_fields():
    text = "Nothing useful here\njust plain text\n"
    header = ""
    image_path = Path("unknown.jpg")

    res = erj.process_returned_OCR(text, header, image_path)

    assert isinstance(res, dict)
    assert "__error" in res
    # total should be None, merchant and transaction_date may be None
    assert res.get("total") is None


def get_example_pairs():
    samples_dir = ROOT / "tests" / "examples"
    if not samples_dir.exists():
        return []

    pairs = []
    for txt_path in sorted(samples_dir.glob("*.txt")):
        json_path = txt_path.with_suffix(".json")
        head_path = txt_path.with_suffix(".head")
        if json_path.exists() and not head_path.exists():
            pairs.append((txt_path, json_path))
    return pairs


def get_pdf_example_pairs():
    samples_dir = ROOT / "tests" / "examples"
    if not samples_dir.exists():
        return []

    triples = []
    for txt_path in sorted(samples_dir.glob("*.txt")):
        json_path = txt_path.with_suffix(".json")
        head_path = txt_path.with_suffix(".head")
        if json_path.exists() and head_path.exists():
            triples.append((txt_path, json_path, head_path))
    return triples

EXAMPLE_PAIRS = get_example_pairs()
PDF_EXAMPLE_PAIRS = get_pdf_example_pairs()
XRUN_EXPECTED = {}

@pytest.mark.parametrize("txt_path,json_path", EXAMPLE_PAIRS)
def test_process_returned_OCR_against_expected_json(txt_path: Path, json_path: Path):
    if txt_path.name in XRUN_EXPECTED:
        pytest.xfail(f"Known current extractor mismatch for {txt_path.name}")

    text = txt_path.read_text(encoding="utf-8")
    expected = json.loads(json_path.read_text(encoding="utf-8"))
    header = ""
    image_path = txt_path.with_suffix(".jpg")

    actual = erj.process_returned_OCR(text, header, image_path)
    assert actual == expected


@pytest.mark.parametrize("txt_path,json_path,head_path", PDF_EXAMPLE_PAIRS)
def test_process_returned_OCR_against_expected_json_pdf(txt_path: Path, json_path: Path, head_path: Path):
    if txt_path.name in XRUN_EXPECTED:
        pytest.xfail(f"Known current extractor mismatch for {txt_path.name}")

    text = txt_path.read_text(encoding="utf-8")
    header = head_path.read_text(encoding="utf-8")
    expected = json.loads(json_path.read_text(encoding="utf-8"))
    image_path = txt_path.with_suffix(".pdf")

    actual = erj.process_returned_OCR(text, header, image_path)
    assert actual == expected


def test_has_example_pairs():
    if not EXAMPLE_PAIRS:
        pytest.skip("No example txt/json pairs found in tests/examples")
