from playwright.sync_api import sync_playwright
import os
import requests

def run():
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
            except Exception as e:
                print(f"Error writing to token.txt: {e}")
        else:
            print("\nNo 'Authorization' headers detected. Check if your credentials are correct.")
            exit


        # browser.close()

        print("Script execution paused.")
        print("The browser will remain open so you can inspect it.")
        print("Press ENTER in this terminal window to close the browser and finish.")
        print("="*40)
        input()

if __name__ == "__main__":
    run()