Wave Enter Expense — Playwright automation

This folder contains a Playwright-based automation script to create withdrawal transactions in Wave using JSON input and receipt files.

Quick setup

1. Change to the skill folder:
```bash
cd .github/skills/wave-enter-expense
```
2. Install dependencies and browsers:
```bash
npm install
npx playwright install --with-deps
```
3. Create your secret password file (the real password) at `secrets/wave_password.txt`.
4. Update `config.local.yaml` with your email and `password_file` path (default points to `secrets/wave_password.txt`).
5. Put receipt files in the `input/` folder. Filenames should follow the pattern: `<Merchant> - <YYYY-MM-DD>.<ext>` (matching is case-insensitive and tolerant of extra spaces).
6. Edit or replace the sample `input/expenses.json` with your records.

Run

```bash
# run in visible (non-headless) mode - default
node playwright/enter_expenses.js --config config.local.yaml --input input/expenses.json

# run headless:
node playwright/enter_expenses.js --config config.local.yaml --input input/expenses.json --headless
```

Notes

- The script tries multiple selector strategies to interact with Wave's UI; if Wave's UI changes, you may need to tweak selectors in `playwright/enter_expenses.js`.
- The script uses the `password_file` entry in `config.local.yaml` to read the password. Do not commit the real password file.
- If the script cannot attach a receipt via `input[type=file]`, it will warn but continue.
