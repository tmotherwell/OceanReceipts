# Repository Contents

## GmailMultiPrint
It is common to receive business receipts via email. This browser extension allows you to export multiple Gmail threads to local PDF files all in one shot (vs the current approach of using the print dialogue to save them one by one). Note PDFs attached to emails are not included, those must be downloaded directly. Recommend to turn OFF chrome setting that prompts for file location of each download

**Chrome:**
1. Go to Manage Extensions
2. Select Load Unpacked
3. Navigate to the Chrome folder, hit select
4. Verify it's active: Navigate to Gmail, select 2 or more threads, look for a floating blue button to appear in the bottom right corner

**Firefox:**

1. Enter "about:debugging" in the URL bar
2. Select "This Firefox"
3. Click "Load Temporary Add-on"
4. Open the Firefox folder and select any file inside
5. The extension remains installed until you remove it or restart Firefox
6. Verify it's active: Navigate to Gmail, select 2 or more threads, look for a floating blue button to appear in the bottom right corner


## ReceiptEntry
This set of Python scripts automates the entry of receipt transactions and images into Wave Accounting. I made this primarily because I didn't want to pay $20/mo for their receipt scanning service (which used to be free, hi enshittification!). It uses Google Vision as an OCR backend since it is available to anyone with a google account and is free for the first 1000 requests per month (I don't have *nearly* that many receipts, but your use case may be different). The script uploads transactions and receipts by mimicking the requests sent by the front-end, so it should be robust even if the UI changes.

### Script Workflow
1. Scan input image/pdf file folder, send to Google Vision for OCR
2. Parse OCR results and extract Transaction Date, Merchant, and Total
3. Write extracted results to output JSON file
4. Rename input files to match scanned results (*date_merchant_uniqueNumber*)
5. Log in to Wave using Playwright and retrieve auth token from request headers
6. Upload transaction via GraphQL HTTP request
7. Upload receipt image via GraphQL HTTP request
8. Link receipt image to receipt transaction via GraphQL HTTP request
9. Move receipt image to long term archive folder and delete JSON files

### Setup

0. Clone repository to local folder of your choice
1. Set up Google Vision on your machine (follow the [guide](https://docs.cloud.google.com/vision/docs/setup))
2. Install python 3.xx to your machine
3. Install the [python VSCode extension](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace)
4. Open VSCode, Create a virtual python environment
    1. Open VSCode Command Pallette (Ctrl-Shift-P)
    2. Type Python Create Environment
    3. Select Venv
    4. Select your python.exe install location
    5. Check the dependencies box, make sure it points to ReceiptEntry\requirements.txt, hit OK
    6. In the terminal, type 'playwright install' and hit enter
5. Create a secrets.txt containing your Wave credentials (see Configuation for format or to change filename), store in ReceiptEntry folder
6. Run ExtractID.py to get your Wave account IDs
7. Set script config values (see below)
8. Add common merchants to merchants.json to improve matching (this is helpful when the merchant name is not present in all the common places, mostly happens with email receipts)
9. Run BeginExpenseEntry.py to begin

### Configuration (config.py)
**File Paths**
1. jsonDir: Set the folder path the output JSON is stored in before entering into Wave
2. receiptInputDir: Set the folder path the input images are stored in
3. receiptStorageRoot: Set the root of the long term archive folder, receipts are stored in folders based on their year (e.g. a receipt with transaction date Dec 19, 2026 would be stored in receiptStorageRoot\2026)
4. credentialsFilename: name of txt file containing your Wave account credentials. Line one should be your username (email), line 2 should be your password

**Account IDs**
1. businessID: Alphanumeric string representing your business in Wave. Extracted from HTTP requests, note this is not the string contained in your URL
2. uncategorizedExpenseAccountID: Wave account ID for uncategorized expenses. Recommended to have all auto-imported expenses end up there so that they can be easily filtered for later (in case of errors)
3. sourceAccountID: Wave account ID for where the money is coming from. Typically shareholder loan for expenses paid by personal credit card

**Automation Settings**
1. loginURL: Sign-in URL for Wave
2. loginTimeout: Amount of time to wait for the Wave dashboard before considering login failed and abort
3. maxRetries: numbers of times to retry transaction posting or receipt uplaod/linking

**Debug Settings**
1. debug_SaveReturnedOCR: dumps raw OCR output to a txt file along with the JSON for troubleshooting and improving detection rules
2. debug_SaveHAR: Saves all HTTP requests to an output HAR for debugging and troubleshooting posting failures
3. debug_harOutputFilename: filename for HAR file