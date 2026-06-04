# Repository Contents

## GmailMultiPrint
It is common to receive business receipts via email. This browser extension allows you to export multiple Gmail threads to local PDF files all in one shot (vs the current approach of using the print dialogue to save them one by one). Note that attached PDFs are not included, those must be downloaded directly. Recommend to turn chrome setting to prompt for file location of each download OFF

**Chrome:**
1. Go to Manage Extensions
2. Select Load Unpacked
3. Navigate to the Chrome folder, hit select
4. Verify it's active: Navigate to Gmail, select 2 or more threads, look for a floating blue button to appear in the bottom right corner

**Firefox:**


## ReceiptEntry
This set of Python scripts automates the entry of receipt transactions and images into Wave Accounting

### Workflow
1. Scan input image/pdf files, send to Google Vision for OCR
2. Parse results and extract Transaction Date, Merchant, and Total
3. Write results to output JSON file
4. Rename input files to match scanned results (*date_merchcnt*)
5. Log in to Wave using Playwright and retrieve auth token from request headers
6. Upload transaction via GraphQL HTTP request
7. Upload receipt image
8. Link receipt image to receipt transaction
9. Move receipt image to long term archive folder and delete JSON files

### Setup

1. Set up Google Vision
2. Set up python packages by installing requirements.txt
3. Set script config values (see below)
4. Run BeginExpenseEntry.py to begin

### Configuration (config.py)
**File Paths**
1. jsonDir: Set the folder path the output JSON is stored in before entering into Wave
2. receiptInputDir: Set the folder path the input images are stored in
3. receiptStorageRoot: Set the root of the long term archive folder, receipts are stored in folders based on their year (e.g. a receipt with transaction date Dec 19, 2026 would be stored in receiptStorageRoot\2026)
4. credentialsFilename: name of txt file containing your Wave account credentials. Line one should be your username (email), line 2 should be your password

**Account IDs**
1. businessID: Alphanumeric string representing your business in Wave. Extracted from HTTP requests, note this is not the string contained in your URL
2. uncategorizedExpenseAccountID: Wave account ID for uncategorized expenses
3. sourceAccountID: Wave account ID for where the money is coming from. Typically shareholder loan for expenses paid by personal credit card

**Automation Settings**
1. loginURL: Sign-in URL for Wave
2. loginTimeout: Amount of time to wait for the Wave dashboard before considering login failed and abort
3. maxRetries: numbers of times to retry transaction posting or receipt uplaod/linking

**Debug Settings**
1. debug_SaveReturnedOCR: dumps raw OCR output to a txt file along with the JSON for troubleshooting and improving detection rules
2. debug_SaveHAR: Saves all HTTP requests to an output HAR for debugging and troubleshooting posting failures
3. debug_harOutputFilename: filename for HAR file