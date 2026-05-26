from playwright.sync_api import sync_playwright
import os
import requests
import json

def getBrowserToken():
    # 1. Read credentials securely
    if not os.path.exists('secrets.txt'):
        print("Error: secrets.txt missing.")
        return

    with open('secrets.txt', 'r') as f:
        credentials = [line.strip() for line in f.readlines() if line.strip()]
        if len(credentials) < 2:
            print("Error: secrets.txt must have username on line 1 and password on line 2.")
            return
        username, password = credentials[0], credentials[1]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Set to store unique tokens found
        tokens_found = set()

        # 2. Monitor Request Headers
        def check_headers(container):
            # Playwright headers are a dictionary
            headers = container.headers
            auth_header = headers.get("authorization") or headers.get("Authorization")
            
            if auth_header:
                # Often tokens are 'Bearer <token>', so we strip 'Bearer ' if present
                clean_token = auth_header.replace("Bearer ", "").replace("bearer ", "").strip()
                if "client" in clean_token.lower():
                        return
                if clean_token not in tokens_found:
                    tokens_found.add(clean_token)
                    print(f"Found Token in {type(container).__name__} Headers: {clean_token}")

        # Attach listeners to both requests and responses
        page.on("request", lambda request: check_headers(request))
        page.on("response", lambda response: check_headers(response))

        # 3. Execution flow
        print("Starting login sequence...")
        page.goto("https://my.waveapps.com/login/")

        # Selectors may need adjustment based on your target site
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        
        # Click and wait for the app to actually use the token
        page.click('#js-sign-in-form button[type="submit"]')
        
        # We wait for 'networkidle' because the token usually appears 
        # in the XHR requests that happen immediately after login.
        page.wait_for_url(lambda url: "/dashboard" in url, timeout=15000)

        # 4. Summary
        if tokens_found:
            print(f"\nSuccess! Captured {len(tokens_found)} unique authorization token(s).")
            # Loop through the set and print every single captured token
            try:
                with open('token.txt', 'w', encoding='utf-8') as token_file:
                    for index, token in enumerate(tokens_found, start=1):
                        token_file.write(f"{token}")
                print("All captured tokens have been saved to 'token.txt'.")
                return {token}
            except Exception as e:
                print(f"Error writing to token.txt: {e}")
        else:
            print("\nNo 'Authorization' headers detected. Check if your credentials are correct.")
            exit

def assembleReceipts():
    # Placeholder for the function that will assemble a dictionary of receipt JSON and receipt image files
    pass

def postTransaction(auth_token, receipt_data):
    import json
    import requests

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
            "businessId": "QnVzaW5lc3M6ZTQ1N2YwZjQtMzM4OC00NDM3LWI3YjUtZWU2NTI1ZWE5YWRi", # Replace with your real base64 ID if different
            "date": "2026-05-18",
            "description": "Automated Test Expense",
            "anchorLineItem": {
                "category": {
                    "type": "ACCOUNT_ID",
                    "accountId": "QWNjb3VudDo1OTg3OTgyMzc1MDMxMTkxMDI7QnVzaW5lc3M6ZTQ1N2YwZjQtMzM4OC00NDM3LWI3YjUtZWU2NTI1ZWE5YWRi"
                },
                "amount": "100.00",
                "itemType": "CREDIT"
            },
            "lineItems": [
                {
                    "category": {
                        "type": "ACCOUNT_ID",
                        "accountId": "QWNjb3VudDo1OTg3OTgyMzgzMTY4MTQxMTI7QnVzaW5lc3M6ZTQ1N2YwZjQtMzM4OC00NDM3LWI3YjUtZWU2NTI1ZWE5YWRi"
                    },
                    "amount": "100.00",
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
        
        # Check if GraphQL itself threw an validation error despite a 200 OK network connection
        errors = response_json.get("data", {}).get("transactionCreate", {}).get("inputErrors")
        success = response_json.get("data", {}).get("transactionCreate", {}).get("didSucceed")
        
        if success:
            print("Expense created successfully in Wave!")
            print(json.dumps(response_json.get("data", {}).get("transactionCreate", {}).get("transaction"), indent=2))
        else:
            print("GraphQL Error encountered:")
            print(json.dumps(errors, indent=2))
    else:
        print(f"HTTP Network request failed with status code: {response.status_code}")
        print(response.text)

def uploadReceipt(business_id, auth_token, file_path):
    url = f"https://api.waveapps.com/businesses/{business_id}/attachments/"
    
    headers = {
        "authorization": f"Bearer {auth_token}",
        "origin": "https://next.waveapps.com",
        "referer": "https://next.waveapps.com/"
    }

    # requests handles the multipart boundary automatically when using the 'files' parameter
    with open(file_path, 'rb') as f:
        files = {
            'file': (file_path, f, 'application/pdf') 
        }
        print(f"Uploading {file_path}...")
        response = requests.post(url, headers=headers, files=files)
        
    if response.status_code == 200 or response.status_code == 201:
        attachment_data = response.json()
        print("✅ File uploaded successfully!")
        return attachment_data.get("id") # Keep this ID for Step 2
    else:
        print(f"❌ Upload failed: {response.text}")
        return None

def linkReceiptToTransaction(business_id, auth_token, transaction_id, attachment_id, sequence=1):
    url = "https://gql.waveapps.com/graphql/internal"
    
    headers = {
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json",
        "origin": "https://next.waveapps.com",
        "referer": "https://next.waveapps.com/"
    }

    # The InlineTransactionPatch mutation
    graphql_query = """
    mutation InlineTransactionPatch($input: TransactionPatchInput!) {
      transactionPatch(input: $input) {
        didSucceed
        inputErrors {
          message
          __typename
        }
        __typename
      }
    }
    """

    # Format the payload based on the HAR trace
    variables = {
        "input": {
            "id": transaction_id, 
            "sequence": sequence, # Usually '1' if you just created it
            "attachment": {
                "id": attachment_id,
                "type": "RECEIPT"
            }
        }
    }

    payload = {
        "operationName": "InlineTransactionPatch",
        "variables": variables,
        "query": graphql_query
    }

    print("Linking receipt to transaction...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        res_json = response.json()
        if res_json.get("data", {}).get("transactionPatch", {}).get("didSucceed"):
            print("🎉 Receipt successfully linked to the transaction!")
        else:
            print("❌ GraphQL Error linking receipt:")
            print(json.dumps(res_json, indent=2))
    else:
        print("❌ Network error linking receipt.")

if __name__ == "__main__":
    bearerToken = getBrowserToken()
    receiptDict = assembleReceipts()