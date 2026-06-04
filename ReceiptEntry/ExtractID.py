from playwright.sync_api import sync_playwright
import os
import json
import time
import re
import config

def _get_post_data(request):
    try:
        val = request.post_data
        if callable(val):
            val = val()
        return val or ''
    except Exception:
        try:
            return request.post_data()
        except Exception:
            return ''


def _find_account_objects(obj):
    """Recursively extract all objects with 'id' and 'name'/'accountName' fields."""
    results = []
    if isinstance(obj, dict):
        # Check if this dict itself is an account object
        if 'id' in obj and ('name' in obj or 'accountName' in obj):
            results.append(obj)
        # Recurse into all values
        for v in obj.values():
            results.extend(_find_account_objects(v))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_find_account_objects(item))
    return results


def getIDs(page, timeout=60):
    username = password = None
    if os.path.exists(getattr(config, 'credentialsFilename', '')):
        try:
            with open(config.credentialsFilename, 'r', encoding='utf-8') as f:
                credentials = [line.strip() for line in f.readlines() if line.strip()]
                if len(credentials) >= 2:
                    username, password = credentials[0], credentials[1]
        except Exception:
            pass

    id_dict = {}
    state = {'found_request': False, 'found_response': False}

    def parse_possible_business_from_vars(vars_obj):
        if not isinstance(vars_obj, dict):
            return None
        for k in ('businessId', 'businessID', 'business', 'business_id'):
            if k in vars_obj and isinstance(vars_obj[k], str):
                return vars_obj[k]
        for v in vars_obj.values():
            if isinstance(v, str) and v.startswith('QnV'):
                return v
        return None

    def find_accounts_in_graphql_response(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower().endswith('accounts') and isinstance(v, list):
                    return v
            for v in obj.values():
                res = find_accounts_in_graphql_response(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = find_accounts_in_graphql_response(item)
                if res:
                    return res
        return None

    def handle_request(request):
        try:
            if 'gql.waveapps.com/graphql' in request.url and request.method == 'POST':
                post = _get_post_data(request)
                if not post:
                    return
                data = None
                try:
                    data = json.loads(post)
                except Exception:
                    m = re.search(r'variables=({.*})', post)
                    if m:
                        try:
                            vars_json = json.loads(m.group(1))
                            opm = re.search(r'operationName=([^&\n]+)', post)
                            data = {'operationName': opm.group(1) if opm else None, 'variables': vars_json}
                        except Exception:
                            data = None
                if not data:
                    return
                op = data.get('operationName')
                if op == 'ListAccountsForCategory':
                    state['found_request'] = True
                    vars_obj = data.get('variables', {})
                    business_id = parse_possible_business_from_vars(vars_obj)
                    if business_id:
                        id_dict['business'] = business_id
                    accounts_var = None
                    for key in ('accounts', 'accountIds', 'account_ids', 'accountIdsToInclude'):
                        if key in vars_obj:
                            accounts_var = vars_obj[key]
                            break
                    if isinstance(accounts_var, list):
                        for acc in accounts_var:
                            if isinstance(acc, dict):
                                name = acc.get('name') or acc.get('accountName')
                                aid = acc.get('id') or acc.get('accountId')
                                if name and aid:
                                    id_dict[name] = aid
        except Exception as e:
            print('Request handler error:', e)

    def handle_response(response):
        try:
            if 'gql.waveapps.com/graphql' in response.url and response.request.method == 'POST':
                req_post = _get_post_data(response.request)
                if not req_post:
                    return
                try:
                    req_data = json.loads(req_post)
                except Exception:
                    return
                if req_data.get('operationName') != 'ListAccountsForCategory':
                    return
                try:
                    text = response.text()
                    body = json.loads(text)
                except Exception:
                    return
                if 'business' not in id_dict:
                    def find_business(o):
                        if isinstance(o, dict):
                            for k, v in o.items():
                                if k.lower() in ('businessid', 'business_id', 'business') and isinstance(v, str):
                                    return v
                                if k.lower() == 'business' and isinstance(v, dict):
                                    return v.get('id')
                            for v in o.values():
                                res = find_business(v)
                                if res:
                                    return res
                        elif isinstance(o, list):
                            for it in o:
                                res = find_business(it)
                                if res:
                                    return res
                        return None
                    biz = find_business(body)
                    if biz:
                        id_dict['business'] = biz
                accounts = _find_account_objects(body)
                print(f"Found {len(accounts)} account objects in response")
                for acc in accounts:
                    name = acc.get('name') or acc.get('accountName') or acc.get('title')
                    aid = acc.get('id') or acc.get('accountId') or acc.get('account_id')
                    if name and aid:
                        id_dict[name] = aid
                        print(f"  Added account: {name}")
                state['found_response'] = True
        except Exception as e:
            print('Response handler error:', e)

    page.on('request', handle_request)
    page.on('response', handle_response)

    try:
        page.goto(config.loginURL)
        if username and password:
            try:
                page.fill('input[name="username"]', username)
                page.fill('input[name="password"]', password)
                page.click('#js-sign-in-form button[type="submit"]')
                page.wait_for_url(lambda url: '/dashboard' in url, timeout=getattr(config, 'loginTimeout', 30000))
            except Exception:
                pass
        try:
            business_url = page.url.rsplit("/", 2)[0]
            page.goto(business_url + "/transactions")
        except Exception:
            pass
    except Exception as e:
        print('Navigation/login error:', e)

    start = time.time()
    while time.time() - start < timeout:
        if state['found_response'] or (state['found_request'] and id_dict.get('business') and len(id_dict) > 1):
            break
        time.sleep(0.2)

    try:
        page.off('request', handle_request)
        page.off('response', handle_response)
    except Exception:
        pass

    return id_dict


def assembleIDJSON(idPayload):
    return json.dumps(idPayload, indent=2)


def main():
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        rawIDPayload = getIDs(page)
        print(f"\nFinal extracted IDs count: {len(rawIDPayload) - 1 if 'business' in rawIDPayload else len(rawIDPayload)} accounts + business id")
        if rawIDPayload:
            out = assembleIDJSON(rawIDPayload)
            try:
                with open('accountIDs.json', 'w', encoding='utf-8') as fh:
                    fh.write(out)
                print('Saved accountIDs.json')
            except Exception as e:
                print('Error saving accountIDs.json:', e)
    finally:
        try:
            playwright.stop()
        except Exception:
            pass


if __name__ == '__main__':
    main()
