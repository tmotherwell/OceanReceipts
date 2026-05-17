from playwright.sync_api import sync_playwright
import os

def run():
    # 1. Read credentials securely
    if not os.path.exists('C:\\Users\\tmotherwell\\Documents\\secrets.txt'):
        print("Error: secrets.txt missing.")
        return

    with open('C:\\Users\\tmotherwell\\Documents\\secrets.txt', 'r') as f:
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
                if clean_token not in tokens_found:
                    tokens_found.add(clean_token)
                    print(f"✨ Found Token in {type(container).__name__} Headers: {clean_token[:30]}...")

        # Attach listeners to both requests and responses
        page.on("request", lambda request: check_headers(request))
        page.on("response", lambda response: check_headers(response))

        # 3. Execution flow
        print("Starting login sequence...")
        page.goto("https://my.waveapps.com/login/")

        # Selectors may need adjustment based on your target site
        page.fill('input[name="id_username"]', username)
        page.fill('input[name="password-input"]', password)
        
        # Click and wait for the app to actually use the token
        page.click('button#sign-in-button js-track-segment-click')
        
        # We wait for 'networkidle' because the token usually appears 
        # in the XHR requests that happen immediately after login.
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000) # Short buffer for any delayed async calls

        # 4. Summary
        if tokens_found:
            print(f"\nCaptured {len(tokens_found)} unique token(s).")
        else:
            print("\nNo 'Authorization' headers detected.")

        browser.close()

if __name__ == "__main__":
    run()