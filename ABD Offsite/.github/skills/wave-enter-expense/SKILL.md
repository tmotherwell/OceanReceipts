---
name: wave-enter-expense
description: '**WORKFLOW SKILL** — Enter expense transactions from JSON into Wave (manual browser steps / human-supervised automation). Use when you need to create withdrawals in Wave and attach receipts located in this skill’s input folder.'
author: Workspace automation
version: 0.1.0
inputs:
  - name: config_file
    description: Path to local config (see Prerequisites). Recommended: config.local.yaml (do NOT commit).
    required: true
  - name: input_json
    description: JSON file or array of expense objects to process (see Input JSON Schema).
    required: true
tags: [wave, accounting, transactions, expenses, ui-automation]
---

# Overview

This skill describes a deterministic, step-by-step workflow to enter expense transactions into Waveapps.com using data from JSON and receipts stored in the skill's input folder. The steps are manual UI actions (clicks/typing); use for human-supervised automation or to implement Playwright/selenium flows.

# Use when

- You need to add single or multiple expense withdrawals into Wave.
- Receipts are stored in the skill folder `input/` and named "<Merchant> - <YYYY-MM-DD>.<ext>".

# Prerequisites

- A Wave account with the credentials stored in a local, non-committed config file (see "Configuration" below).
- The skill folder contains an `input/` directory with receipt files named exactly: `<Merchant> - <Date>` (example: `Aramark - 2025-04-08.pdf`).
- A JSON file (or array) with expense objects matching the schema below.
- This workflow assumes no 2FA for the Wave account; no 2FA pause is included.

# Configuration

- Create a local config file: `.github/skills/wave-enter-expense/config.local.yaml` (add to `.gitignore`). Example:
```yaml
email: "user@example.com"
# Do NOT store plaintext passwords in repo. Preferred: a local secret file.
password_file: "secrets/wave_password.txt" # relative to this skill folder; file should contain the password only
input_folder: "input"
receipt_pattern: "{merchant} - {date}" # pattern used to match receipt filenames
```
Create the secret file specified by `password_file` (see `secrets/wave_password.txt.example`) before running automation.

# Input JSON Schema

Each record must contain:
- `date` (string): YYYY-MM-DD
- `merchant` (string): merchant name used for Description & receipt lookup
- `total` (number): amount (positive) — currency assumed by Wave account

Example single object:
```json
{
  "date": "2025-04-08",
  "merchant": "Aramark",
  "total": 123.45
}
```
Or an array of objects.

# File layout (skill folder)

- `.github/skills/wave-enter-expense/SKILL.md` (this file)
- `.github/skills/wave-enter-expense/input/` (receipt files)
- `.github/skills/wave-enter-expense/config.local.yaml` (local credentials — do NOT commit)

# Step-by-step Workflow

For each expense record in the input JSON:
1. Open https://www.waveapps.com/ in a browser.
2. Click "Log In".
3. Type the `email` from the local config and click Next.
4. Type the password read from the local secret file referenced by `password_file` in the config and click "Sign In".
5. In the left sidebar click "Accounting", then "Transactions".
6. Click "Add transaction" → "Add withdrawal".
7. Fill fields:
   - Date: use `date` (YYYY-MM-DD).
   - Description: use `merchant`.
   - Account: set to "Shareholder Loan".
   - Amount: use `total` (enter as positive number for withdrawal).
8. Under the Receipt header, click "Select a file".
9. In the file picker, navigate to the skill `input/` folder and select the file that matches `<Merchant> - <Date>` using case-insensitive matching and ignoring extra spaces.
   - Matching rules:
     - Normalize both merchant and filenames by trimming, collapsing multiple spaces to a single space, and converting to lowercase.
     - Exact normalized match first: `{merchant} - {date}.*`
     - If multiple normalized matches, prefer the filename that most closely matches the original merchant text; if still ambiguous, pick the most recently modified file.
     - If no file found, continue without attachment and add a note to the transaction: "Receipt not found".
10. Click "Open" in the file picker, wait 5 seconds to ensure upload completes.
11. Click "Save" to save the transaction.
12. Repeat for next record.

# Branching & Error Handling

- Missing receipt: attach none, add a note, continue.
- Login failures: abort and report error.
- Amount format: `total` is expected to be a plain positive number; the agent will validate it's numeric before typing.
- Page layout changes: if a step can't find a UI element, stop and surface a screenshot and DOM hint for manual remediation.

# Quality Criteria (Completion Checks)

- Transaction exists in Wave with correct Date, Description, Account, and Amount.
- Receipt successfully attached (if file present).
- Save confirmed (no validation errors).
- Log entry created locally for the processed JSON record with timestamp and receipt filename (if any).

# Examples

Sample JSON (array form):
```json
[
  {
    "date": "2025-04-08",
    "merchant": "Aramark",
    "total": 123.45
  },
  {
    "date": "2025-04-09",
    "merchant": "Cafe Blue",
    "total": 45.0
  }
]
```
Receipt filenames expected in `input/`:
- `Aramark - 2025-04-08.pdf`
- `Cafe Blue - 2025-04-09.jpg`

# Invocation Prompts / How to Use

- "Run the Wave expense entry skill on `.github/skills/wave-enter-expense/input/expenses.json` using `.github/skills/wave-enter-expense/config.local.yaml`."
- "Process 1 record: date 2025-04-08 merchant Aramark total 123.45."

# Resolved decisions

- Local config location: `.github/skills/wave-enter-expense/config.local.yaml`.
- Credentials: use a local secret file (see `password_file` in the sample config).
- `total` format: always a plain positive number (agent will validate numeric).
- Receipt matching: case-insensitive and tolerant of extra spaces.
- 2FA: not used for this account; no 2FA handling required by the workflow.

# Next Customizations (suggested)

- Add a small wrapper prompt/script to process a full JSON file and run this skill for each record.
- Implement Playwright script to fully automate UI interactions (credentials via secret manager).
- Add a "dry-run" mode that opens Wave, fills the form but does not click "Save" for verification.
- Add automated receipt OCR fallback: if filename missing, try to match by merchant and date using OCR text.

# Security & Privacy

- Never commit `config.local.yaml` containing credentials. Add `.github/skills/wave-enter-expense/config.local.yaml` to your `.gitignore`.
- Prefer environment variables or OS keyring for passwords.
- Log only metadata (filenames, timestamps), never raw passwords.

---

That’s the initial SKILL.md draft. Update the `input/` folder and `config.local.yaml` as needed before using.