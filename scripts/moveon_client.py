import os
import sys
import re
import urllib.request
import urllib.error
import json
import uuid
import time
from typing import Dict, List, Any, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MOVEON_LOGIN_URL = "https://moveon.global/auth/login"
MOVEON_SESSION_PATH = os.path.join(WORKSPACE_ROOT, ".moveon_session.json")

def extract_product_id_from_url(url_or_id: str) -> str:
    """
    Extracts the internal MoveOn composite product ID from a MoveOn URL or raw ID.
    MoveOn product URLs follow the pattern:
    https://moveon.global/BD_en/products/{part1}-{slug}/{part2}
    MoveOn internal API expects: {part2}{part1}
    """
    url_or_id = url_or_id.strip()
    
    # Check if URL matches the MoveOn product structure
    match = re.search(r'/products/([A-Za-z0-9]+)[^/]*/([A-Za-z0-9]+)', url_or_id)
    if match:
        part1 = match.group(1)
        part2 = match.group(2)
        return f"{part2}{part1}"
    
    # If the user passed raw ID or direct query
    # Check if it's already a composite or single alphanumeric ID
    clean_id = re.sub(r'[^A-Za-z0-9]', '', url_or_id)
    return clean_id

def clean_model_name(name: str) -> str:
    """Cleans phone model string, removing Chinese brackets or spec notes like 【1 case】."""
    name = re.sub(r'【[^】]*】', '', name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    name = re.sub(r'\(1\s*case\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^(?:applicable\s+to|suitable\s+for)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\brealme\b', 'Realme', name, flags=re.IGNORECASE)
    name = re.sub(r'\bhonor\b', 'Honor', name, flags=re.IGNORECASE)
    name = re.sub(r'\bhuawei\b', 'Huawei', name, flags=re.IGNORECASE)
    name = re.sub(r'\biphone\b', 'iPhone', name, flags=re.IGNORECASE)
    name = re.sub(r'\bgalaxy\b', 'Galaxy', name, flags=re.IGNORECASE)
    name = re.sub(r'\bsamsung\b', 'Samsung', name, flags=re.IGNORECASE)
    name = re.sub(r'\bredmi\b', 'Redmi', name, flags=re.IGNORECASE)
    name = re.sub(r'\bxiaomi\b', 'Xiaomi', name, flags=re.IGNORECASE)
    name = re.sub(r'\bneo\s*(\d+)\b', r'Neo\1', name, flags=re.IGNORECASE)
    name = re.sub(r'\bx(\d+)\s*promax\b', r'X\1 Pro Max', name, flags=re.IGNORECASE)
    name = re.sub(r'\bx(\d+)\s*pro\b', r'X\1 Pro', name, flags=re.IGNORECASE)
    name = re.sub(r'\bx(\d+)\s*gt\b', r'X\1 GT', name, flags=re.IGNORECASE)
    name = re.sub(r'\bx(\d+)\s*i\b', r'X\1i', name, flags=re.IGNORECASE)
    name = re.sub(r'\bx(\d+)\b', r'X\1', name, flags=re.IGNORECASE)
    name = re.sub(r'[\\/:*?"<>|]', '_', name)  # Windows-safe filename characters
    return name.strip()

def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be safely used as a filename."""
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def load_env(env_path: Optional[str] = None) -> Dict[str, str]:
    """Lightweight .env reader without external dependencies."""
    if env_path is None:
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    env_vars = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    env_vars[k] = v
                    if k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass
    return env_vars

def login_moveon(email: Optional[str] = None, password: Optional[str] = None, headless: bool = True) -> Optional[str]:
    """
    Logs in to MoveOn (https://moveon.global/auth/login) using email and password via Playwright.
    Extracts the Bearer auth token and persists session cookies to .moveon_session.json.
    """
    load_env()
    email = email or os.environ.get("MOVEON_EMAIL") or os.environ.get("MOVEON_EMAIL_OR_PHONE")
    password = password or os.environ.get("MOVEON_PASSWORD")

    if not email or not password:
        print("[!] MoveOn login credentials not found in .env (MOVEON_EMAIL, MOVEON_PASSWORD).")
        return None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] Playwright is not installed. Automated MoveOn login requires playwright.")
        return None

    captured_tokens = []

    print(f"[*] Launching browser for MoveOn authentication ({email})...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Monitor network responses for token
        def on_response(response):
            try:
                auth_h = response.headers.get("authorization")
                if auth_h and auth_h.startswith("Bearer "):
                    captured_tokens.append(auth_h.replace("Bearer ", "").strip())
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    data = response.json()
                    if isinstance(data, dict):
                        for k in ["token", "auth_token", "access_token", "session_token"]:
                            if k in data and isinstance(data[k], str) and len(data[k]) > 20:
                                captured_tokens.append(data[k])
                        if "session" in data and isinstance(data["session"], dict):
                            for k in ["token", "auth_token", "access_token"]:
                                if k in data["session"] and isinstance(data["session"][k], str) and len(data["session"][k]) > 20:
                                    captured_tokens.append(data["session"][k])
            except Exception:
                pass

        page.on("response", on_response)

        try:
            page.goto(MOVEON_LOGIN_URL, timeout=40000)
            page.wait_for_load_state("networkidle")

            # Fill identifier & password
            page.wait_for_selector("input#identifier, input[placeholder*='email']", timeout=15000)
            page.fill("input#identifier, input[placeholder*='email']", email)
            page.fill("input#password, input[type='password']", password)

            print("[*] Submitting MoveOn login credentials...")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # Check for OTP or additional security step
            if "otp" in page.content().lower() or "verification" in page.content().lower():
                print("\n" + "="*65)
                print(" [!] MoveOn OTP verification prompt detected.")
                otp_code = input(" >> Enter MoveOn verification code: ").strip()
                print("="*65)
                otp_inp = page.query_selector("input[type='number'], input[placeholder*='code'], input[maxlength='6']")
                if otp_inp:
                    otp_inp.fill(otp_code)
                    page.press("input[type='number'], input[placeholder*='code'], input[maxlength='6']", "Enter")
                    time.sleep(3)
                    page.wait_for_load_state("networkidle")

            # Check localStorage for token
            token = None
            try:
                ls_data = page.evaluate("() => { let s = {}; for (let i = 0; i < localStorage.length; i++) { let k = localStorage.key(i); s[k] = localStorage.getItem(k); } return s; }")
                for k in ["token", "auth_token", "mvn-auth-token", "mvn_token", "access_token"]:
                    if k in ls_data and ls_data[k]:
                        token = ls_data[k]
                        break
                if not token and captured_tokens:
                    token = captured_tokens[-1]
                if not token:
                    for k, v in ls_data.items():
                        if any(t in k.lower() for t in ["token", "auth", "session"]) and isinstance(v, str) and len(v) > 20:
                            token = v
                            break
            except Exception as e:
                print(f"[!] Warning reading localStorage: {e}")

            # Save session state
            context.storage_state(path=MOVEON_SESSION_PATH)

            if token:
                try:
                    with open(MOVEON_SESSION_PATH, "r+", encoding="utf-8") as f:
                        s_data = json.load(f)
                        s_data["moveon_token"] = token
                        f.seek(0)
                        json.dump(s_data, f, indent=2)
                        f.truncate()
                except Exception:
                    pass
                print(f"[✓] Successfully authenticated with MoveOn! Token cached in {os.path.basename(MOVEON_SESSION_PATH)}")
            else:
                print(f"[✓] MoveOn authentication complete. Session cookies saved to {os.path.basename(MOVEON_SESSION_PATH)}")

            return token
        finally:
            browser.close()

class MoveOnClient:
    BASE_API = "https://product-api.proxy.service.moveon.global/api/product/customer/v1/products/find"

    def __init__(self, region: str = "BD", locale: str = "en", business_type: str = "wholesale", auth_token: Optional[str] = None):
        load_env()
        self.region = region
        self.locale = locale
        self.business_type = business_type
        self.guest_id = str(uuid.uuid4())

        # 1. Direct parameter or MOVEON_AUTH_TOKEN in .env
        self.auth_token = (auth_token or os.environ.get("MOVEON_AUTH_TOKEN") or "").strip()

        # 2. Check cached session file (.moveon_session.json)
        if not self.auth_token and os.path.exists(MOVEON_SESSION_PATH):
            try:
                with open(MOVEON_SESSION_PATH, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                    self.auth_token = (s_data.get("moveon_token") or "").strip()
            except Exception:
                pass

        # 3. If still no token but MOVEON_EMAIL & MOVEON_PASSWORD are present, auto-login
        if not self.auth_token and (os.environ.get("MOVEON_EMAIL") or os.environ.get("MOVEON_EMAIL_OR_PHONE")) and os.environ.get("MOVEON_PASSWORD"):
            print("    [*] No MOVEON_AUTH_TOKEN found. Logging into MoveOn with email and password...")
            try:
                self.auth_token = login_moveon(headless=True) or ""
            except Exception as e:
                print(f"    [!] Warning: Automated MoveOn login error: {e}")

    def fetch_product(self, url_or_id: str) -> Dict[str, Any]:
        """
        Fetches the product details for the single specified product.
        Strictly does NOT crawl or scan any external or related links.
        """
        product_id = extract_product_id_from_url(url_or_id)
        if not product_id:
            raise ValueError(f"Could not extract a valid MoveOn product ID from: {url_or_id}")

        api_url = f"{self.BASE_API}/{product_id}?region={self.region}&locale={self.locale}&business_type={self.business_type}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://moveon.global',
            'Referer': 'https://moveon.global/',
            'X-GUEST-ID': self.guest_id,
            'X-GUEST-SESSION': self.guest_id
        }
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
            print("    [✓] Crawling as MoveOn Business Account (auth token applied).")
        else:
            print("    [i] Crawling in Guest Wholesale mode (no MOVEON_AUTH_TOKEN or login detected in .env).")

        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                raw_json = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', 'ignore')
            raise RuntimeError(f"MoveOn API error (HTTP {e.code}): {error_body}") from e
        except Exception as e:
            raise RuntimeError(f"Network error communicating with MoveOn API: {e}") from e

        data = raw_json.get('data', {})
        if not data:
            raise ValueError("No product data returned by MoveOn API.")

        title = data.get('title', 'Untitled Phone Cover')
        main_image = data.get('image')
        
        # Parse Gallery Images
        gallery_raw = data.get('gallery', {})
        gallery_items = []
        if isinstance(gallery_raw, dict):
            gallery_items = gallery_raw.get('data', [])
        elif isinstance(gallery_raw, list):
            gallery_items = gallery_raw

        gallery_urls = []
        for item in gallery_items:
            img = item.get('image') if isinstance(item, dict) else item
            if img and img not in gallery_urls:
                gallery_urls.append(img)
        if main_image and main_image not in gallery_urls:
            gallery_urls.insert(0, main_image)

        # Parse Properties & Model Options
        props_data = data.get('variation', {}).get('properties', {}).get('data', [])
        prop_values_map = {}
        model_property_id = None
        models_list = []

        for prop in props_data:
            prop_id = str(prop.get('id', ''))
            prop_name = prop.get('name', '').lower()
            values = prop.get('values', {}).get('data', [])
            
            is_model_prop = any(k in prop_name for k in ['model', 'applicable', 'phone', 'compatible'])
            if not is_model_prop and len(props_data) == 1:
                is_model_prop = True
            
            if is_model_prop and not model_property_id:
                model_property_id = prop_id

            for val in values:
                val_id = str(val.get('id', ''))
                val_name = val.get('name', '')
                prop_values_map[val_id] = {
                    'name': val_name,
                    'prop_id': prop_id,
                    'image': val.get('image')
                }
                if is_model_prop and prop_id == model_property_id:
                    clean_name = clean_model_name(val_name)
                    models_list.append({
                        'id': val_id,
                        'raw_name': val_name,
                        'clean_name': clean_name,
                        'image': val.get('image')
                    })

        # Parse SKUs mapped by model
        skus_data = data.get('variation', {}).get('skus', {}).get('data', [])
        skus_by_model: Dict[str, List[Dict[str, Any]]] = {}

        for sku in skus_data:
            sku_id = str(sku.get('id', ''))
            sku_image = sku.get('image') or main_image
            price_info = sku.get('price', {})
            
            # Find associated properties
            associations = sku.get('property_associations', {}).get('data', [])
            associated_model_clean = None
            variant_names = []

            for assoc in associations:
                val_id = str(assoc.get('property_value_id', ''))
                val_meta = prop_values_map.get(val_id)
                if val_meta:
                    if val_meta['prop_id'] == model_property_id:
                        associated_model_clean = clean_model_name(val_meta['name'])
                    else:
                        variant_names.append(val_meta['name'])

            if not associated_model_clean:
                associated_model_clean = models_list[0]['clean_name'] if models_list else "Standard Model"

            sku_item = {
                'id': sku_id,
                'image': sku_image,
                'variant_label': " - ".join(variant_names) if variant_names else f"SKU {sku_id}",
                'price': price_info
            }

            if associated_model_clean not in skus_by_model:
                skus_by_model[associated_model_clean] = []
            skus_by_model[associated_model_clean].append(sku_item)

        return {
            'product_id': product_id,
            'title': title,
            'main_image': main_image,
            'gallery_images': gallery_urls,
            'models': models_list,
            'properties': props_data,
            'skus_by_model': skus_by_model,
            'raw_data': data
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MoveOn API Client & Authentication Manager")
    parser.add_argument("--login", action="store_true", help="Log in to MoveOn using credentials in .env and save session")
    parser.add_argument("--headful", action="store_true", help="Run browser visibly for manual interaction or OTP entry")
    parser.add_argument("--url", type=str, help="Fetch and print details for a MoveOn product URL")
    args = parser.parse_args()

    if args.login:
        token = login_moveon(headless=not args.headful)
        if token:
            print(f"[✓] MoveOn authentication successful! Token cached in {os.path.basename(MOVEON_SESSION_PATH)}")
        else:
            print("[!] MoveOn authentication could not retrieve a Bearer token.")
    elif args.url:
        client = MoveOnClient()
        prod = client.fetch_product(args.url)
        print(f"\n[✓] Title: {prod['title']}")
        print(f"    Total Models: {len(prod['models'])}")
        print(f"    Total Gallery: {len(prod['gallery_images'])}")
        print(f"    Total SKUs: {sum(len(v) for v in prod['skus_by_model'].values())}")
    else:
        parser.print_help()
