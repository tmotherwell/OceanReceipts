from playwright.sync_api import sync_playwright
import os
import base64
import requests
import json
import time
import config
import random

# GraphQL internal APIs use the base64-style business ID.
BUSINESS_ID = config.businessID
ATTACHMENT_BUSINESS_UUID = os.getenv("WAVE_ATTACHMENT_BUSINESS_UUID")
HAR_OUTPUT_PATH = config.harOutputFilename

# Some workflows also need the plain UUID business ID for REST endpoints.
def get_business_uuid(base64_business_id):
    try:
        decoded = base64.b64decode(base64_business_id).decode('utf-8')
        if decoded.startswith("Business:"):
            return decoded.split(":", 1)[1]
    except Exception:
        pass
    return base64_business_id

def encode_business_id(business_uuid):
    try:
        raw = f"Business:{business_uuid}"
        return base64.b64encode(raw.encode('utf-8')).decode('utf-8')
    except Exception:
        return None

def build_graphql_attachment_id(attachment_id_or_uuid, attachment_business_uuid=None):
    if not attachment_id_or_uuid:
        return None
    
    # If it's already a base64 encoded string containing the word Receipt, return it
    if "UmVjZWlwd" in attachment_id_or_uuid: # 'Receipt' in base64
        return attachment_id_or_uuid
        
    if attachment_business_uuid and attachment_id_or_uuid.count("-") == 4:
        # 1. Construct the full raw string
        raw_id = f"Business:{attachment_business_uuid};Receipt:{attachment_id_or_uuid}"
        
        # 2. Base64 encode the ENTIRE string
        return base64.b64encode(raw_id.encode('utf-8')).decode('utf-8')
        
    return attachment_id_or_uuid


def getBrowserToken(page):
    # 1. Read credentials securely
    if not os.path.exists(config.credentialsFilename):
        print("Error: credentials file missing.")
        return

    with open(config.credentialsFilename, 'r') as f:
        credentials = [line.strip() for line in f.readlines() if line.strip()]
        if len(credentials) < 2:
            print("Error: credentials file must have username on line 1 and password on line 2.")
            return
        username, password = credentials[0], credentials[1]

    # Set to store unique tokens found
    tokens_found = set()

    # 2. Monitor Request Headers
    def check_headers(container):
        headers = container.headers
        auth_header = headers.get("authorization") or headers.get("Authorization")
        if auth_header:
            clean_token = auth_header.replace("Bearer ", "").replace("bearer ", "").strip()
            if "client" in clean_token.lower():
                return
            if clean_token not in tokens_found:
                tokens_found.add(clean_token)
                print(f"Found Token in {type(container).__name__} Headers: {clean_token}")

    page.on("request", lambda request: check_headers(request))
    page.on("response", lambda response: check_headers(response))

    print("Starting login sequence...")
    page.goto(config.loginURL)

    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('#js-sign-in-form button[type="submit"]')
    page.wait_for_url(lambda url: "/dashboard" in url, timeout=config.loginTimeout)

    if tokens_found:
        print(f"\nSuccess! Captured {len(tokens_found)} unique authorization token(s).")
        return next(iter(tokens_found))
    else:
        print("\nNo 'Authorization' headers detected. Check if your credentials are correct.")
        return None

def postTransaction(auth_token, receipt_json_path):
    if not auth_token:
        print("Error: Missing auth token. Cannot post transaction.")
        return

    try:
        with open(receipt_json_path, 'r', encoding='utf-8') as infile:
            receipt_data = json.load(infile)
    except Exception as e:
        print(f"Error reading receipt JSON {receipt_json_path}: {e}")
        return

    transaction_date = receipt_data.get("transaction_date") or receipt_data.get("date") or "1970-01-01"
    description = receipt_data.get("merchant") or "Unknown Merchant"
    amount = receipt_data.get("total_formatted") or receipt_data.get("total")
    if amount is None:
        amount = "0.00"
    else:
        amount = str(amount)

    # 2. Replicate Wave's Internal API endpoint
    url = "https://gql.waveapps.com/graphql/internal"

    # 3. Define Headers (Including the extracted bearer token)
    headers = {
        "authority": "gql.waveapps.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": f"Bearer {auth_token}",  # <-- Your dynamic token injects here
        "content-type": "application/json",
        "origin": "https://next.waveapps.com",
        "referer": "https://next.waveapps.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    }

    # 4. Define GraphQL Query & Fragments exactly as Wave structured them
    graphql_query = """
    mutation TransactionCreate($input: TransactionCreateInput!) {
    transactionCreate(input: $input) {
        didSucceed
        inputErrors {
        code
        message
        path
        __typename
        }
        transaction {
        ...TransactionFragment
        __typename
        }
        __typename
    }
    }

    fragment AccountFragment on Account {
    id
    name
    accrualAnchorTier
    isArchived
    isPaymentsByWaveAccount
    currency { code __typename }
    subtype { name value type { value __typename } __typename }
    __typename
    }

    fragment SalesTaxFragment on SalesTax {
    id abbreviation name rate isArchived isRecoverable __typename
    }

    fragment TransactionLineItemFragment on ClientTransactionLineItem {
    account { ...AccountFragment __typename }
    amount accountAmount businessAmount
    customer { id name isArchived __typename }
    vendor { id name isArchived __typename }
    description itemType label matchedPeriodId
    matchedPeriod { id endDate status __typename }
    isReconciled order taxAction
    taxSummary {
        totalTaxAmount
        taxLiabilities { accountId isTaxAmountManuallySet amount salesTax { ...SalesTaxFragment __typename } __typename }
        __typename
    }
    meta { metaEntityType __typename }
    autocatCategoryStatus
    tags { id name archived __typename }
    __typename
    }

    fragment TransactionFragment on ClientTransaction {
    id amount notes date dateCreated description direction sequence userModifiedAt verificationStatus
    currency { code __typename }
    origin { externalId description type __typename }
    anchorLineItem { ...TransactionLineItemFragment __typename }
    lineItems { ...TransactionLineItemFragment __typename }
    detailActions { amount date description account category verificationStatus direction notes vendor customer lineItems save split canDelete copy attachment salesTax lineItemAmount __typename }
    listActions { amount date description account category verificationStatus attachment __typename }
    mergedFrom { transactionId __typename }
    mergeSource mergedVerificationState
    attachment { id type __typename }
    missingFields active __typename
    }
    """

    # 5. Define variables (You can customize amount, date, description, and accounts here)
    variables = {
        "input": {
            "businessId": BUSINESS_ID,
            "date": transaction_date,
            "description": description,
            "anchorLineItem": {
                "category": {
                    "type": "ACCOUNT_ID",
                    "accountId": config.shareholderLoanAccountID
                },
                "amount": amount,
                "itemType": "CREDIT"
            },
            "lineItems": [
                {
                    "category": {
                        "type": "ACCOUNT_ID",
                        "accountId": config.uncategorizedExpenseAcccountID
                    },
                    "amount": amount,
                    "itemType": "DEBIT",
                    "taxAction": None
                }
            ]
        }
    }

    # 6. Formulate Payload JSON object
    payload = {
        "operationName": "TransactionCreate",
        "variables": variables,
        "query": graphql_query
    }

    # 7. Post request execution
    print("Sending POST request to Wave GraphQL server...")
    response = requests.post(url, headers=headers, json=payload)

    # 8. Error and verification handling
    if response.status_code == 200:
        response_json = response.json()
        
        # Check if GraphQL itself threw a validation error despite a 200 OK network connection
        errors = response_json.get("data", {}).get("transactionCreate", {}).get("inputErrors")
        success = response_json.get("data", {}).get("transactionCreate", {}).get("didSucceed")
        transaction = response_json.get("data", {}).get("transactionCreate", {}).get("transaction")
        
        if success and transaction:
            transaction_id = transaction.get("id") if isinstance(transaction, dict) else None
            if not transaction_id:
                transaction_id = transaction.get("transaction", {}).get("id") if isinstance(transaction, dict) else None
            print(f"Expense created successfully in Wave! Transaction ID: {transaction_id}")
            print(json.dumps(transaction, indent=2))
            return transaction_id
        else:
            print("GraphQL Error encountered:")
            print(json.dumps(errors, indent=2))
            print(json.dumps(response_json, indent=2))
            return None
    else:
        print(f"HTTP Network request failed with status code: {response.status_code}")
        print(response.text)
        return None


def uploadReceipt(request_context, auth_token, attachment_business_uuid, file_path):
    url = f"https://api.waveapps.com/businesses/{attachment_business_uuid}/attachments/"

    headers = {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9,fr;q=0.8",
        "authorization": f"Bearer {auth_token}",
        "origin": "https://next.waveapps.com",
        "referer": "https://next.waveapps.com/",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": '?0',
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    }

    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    multipart = {
        "file": {
            "name": os.path.basename(file_path),
            "mimeType": "application/pdf",
            "buffer": file_bytes,
        }
    }

    print(f"Uploading {file_path} to business {attachment_business_uuid} via Playwright request context...")
    response = request_context.post(url, headers=headers, multipart=multipart)

    if response.status == 200 or response.status == 201:
        attachment_data = response.json()
        raw_attachment_id = attachment_data.get("id") or attachment_data.get("uuid")
        attachment_uuid = raw_attachment_id if raw_attachment_id and raw_attachment_id.count("-") == 4 else None
        if not attachment_uuid:
            print("❌ Upload succeeded but could not determine attachment UUID from response.")
            return None

        print("✅ File uploaded successfully!")
        print(json.dumps(attachment_data, indent=2))
        print(f"Raw attachment identifier: {raw_attachment_id}")

        ready_attachment = wait_for_uploaded_attachment(request_context, auth_token, attachment_business_uuid, attachment_uuid)
        if not ready_attachment:
            print("❌ Attachment did not become available for linking.")
            return None

        attachment_id = build_graphql_attachment_id(attachment_uuid, attachment_business_uuid)
        print(f"Attachment is ready for linking with GraphQL attachment ID: {attachment_id}")
        return attachment_id
    else:
        try:
            body = response.text()
        except Exception:
            body = "<unable to read response body>"
        print(f"❌ Upload failed: {response.status} {body}")
        return None


def get_uploaded_attachment(request_context, auth_token, attachment_business_uuid, attachment_uuid):
    url = f"https://api.waveapps.com/businesses/{attachment_business_uuid}/attachments/"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {auth_token}",
        "origin": "https://next.waveapps.com",
        "referer": "https://next.waveapps.com/",
        "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        "sec-ch-ua-mobile": '?0',
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    }

    response = request_context.get(url, headers=headers, params={"uuid": attachment_uuid, "type": "RECEIPT"})
    if response.status == 200:
        return response.json()
    return None


def wait_for_uploaded_attachment(request_context, auth_token, attachment_business_uuid, attachment_uuid, max_attempts=config.maxRetries, interval_seconds=4):
    for attempt in range(1, max_attempts + 1):
        print(f"Checking attachment readiness ({attempt}/{max_attempts}) for {attachment_uuid}...")
        attachment_data = get_uploaded_attachment(request_context, auth_token, attachment_business_uuid, attachment_uuid)
        if attachment_data:
            status = attachment_data.get("upload_status")
            if status == "success":
                print("✅ Attachment is ready for linking.")
                return attachment_data
            print(f"Attachment status: {status}")
        else:
            print("Attachment lookup returned no object yet.")

        if attempt < max_attempts:
            time.sleep(interval_seconds)

    print("❌ Attachment did not become ready in time.")
    return None

def linkReceiptToTransaction(request_context, business_id, auth_token, transaction_id, attachment_id, sequence=1):
    url = "https://gql.waveapps.com/graphql/internal"
    
    headers = {
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json",
        "origin": "https://next.waveapps.com",
        "referer": "https://next.waveapps.com/"
    }

    # The InlineTransactionPatch mutation, aligned with the browser HAR.
    graphql_query = """
    mutation InlineTransactionPatch($input: TransactionPatchInput!) {
      transactionPatch(input: $input) {
        didSucceed
        inputErrors {
          message
          __typename
        }
        transaction {
          id
          __typename
        }
        sideEffects {
          id
          __typename
        }
        __typename
      }
    }
    """

    variables = {
        "input": {
            "id": transaction_id,
            "sequence": sequence,
            "attachment": {
                "id": attachment_id,
                "type": "RECEIPT"
            }
        }
    }

    payload = {
        "operationName": "InlineTransactionPatch",
        "variables": variables,
        "extensions": {
            "clientLibrary": {
                "name": "@apollo/client",
                "version": "4.1.9"
            }
        },
        "query": graphql_query
    }

    print("Linking receipt to transaction...")
    print(f"Transaction ID: {transaction_id}")
    print(f"Attachment ID: {attachment_id}")

    max_attempts = config.maxRetries
    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts} to link receipt...")
        response = request_context.post(url, headers=headers, data=json.dumps(payload))

        if response.status != 200:
            print(f"❌ Network error linking receipt: HTTP {response.status}")
            print(response.text())
            return False

        try:
            res_json = response.json()
        except ValueError as e:
            print("❌ Failed to parse JSON response from transactionPatch:")
            print(e)
            print(response.text())
            return False

        if not isinstance(res_json, dict):
            print("❌ Unexpected transactionPatch response payload:")
            print(res_json)
            return False

        transaction_patch = res_json.get("data", {}).get("transactionPatch")
        if transaction_patch and transaction_patch.get("didSucceed"):
            print("🎉 Receipt successfully linked to the transaction!")
            return True

        errors = res_json.get("errors") or []
        if any(isinstance(err, dict) and err.get("extensions", {}).get("code") == "NOT_FOUND" for err in errors):
            if attempt < max_attempts:
                print("⚠️ Receipt not found yet. Waiting before retrying...")
                time.sleep(3)
                continue

        print("❌ GraphQL Error linking receipt:")
        print(json.dumps(res_json, indent=2))
        return False

    print("❌ Receipt never became available for linking after retries.")
    return False

def main(receiptPaths):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(record_har_path=HAR_OUTPUT_PATH)
    page = context.new_page()

    try:
        auth_token = getBrowserToken(page)
        if not auth_token:
            print("No auth token available. Aborting post.")
            return

        business_uuid = get_business_uuid(BUSINESS_ID)
        print(f"Using GraphQL business ID: {BUSINESS_ID}")
        print(f"Using attachment business UUID: {business_uuid}")
        if ATTACHMENT_BUSINESS_UUID:
            print("Using explicit WAVE_ATTACHMENT_BUSINESS_UUID override.")
        elif business_uuid != get_business_uuid(BUSINESS_ID):
            print("WARNING: derived attachment UUID differs from the base64 business ID.")

        request_context = context.request
        for json_path, receipt_path in receiptPaths.items():
            print(f"Posting transaction for {json_path}")
            transaction_id = postTransaction(auth_token, json_path)
            time.sleep(random.uniform(2, 5))
            if not transaction_id:
                print(f"Skipping receipt attachment because transaction creation failed for {json_path}")
                continue
            attachment_id = uploadReceipt(request_context, auth_token, business_uuid, receipt_path)
            if not attachment_id:
                print(f"Skipping attachment linking because upload failed for {receipt_path}")
                continue

            linked = linkReceiptToTransaction(request_context, BUSINESS_ID, auth_token, transaction_id, attachment_id)
            if not linked:
                print(f"Failed to link receipt {receipt_path} to transaction {transaction_id}")
    finally:
        try:
            context.close()
            print(f"Saved HAR output to {HAR_OUTPUT_PATH}")
        except Exception as e:
            print(f"Error closing HAR context: {e}")
        try:
            browser.close()
        except Exception:
            pass
        try:
            playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main({})
    