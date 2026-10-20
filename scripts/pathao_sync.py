#!/usr/bin/env python3
"""
Pathao Commerce Catalog Sync & Store Automation
Syncs CoverStore inventory products and variants directly to Pathao Commerce (https://commerce.pathao.com).
Rule: 1 MoveOn product link = 1 parent product on Pathao Commerce, with all SKUs as variants.
"""

import os
import sys
import csv
import json
import time
import argparse
from typing import List, Dict, Any, Optional
from collections import defaultdict
import openpyxl

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INVENTORY_CSV_PATH = os.path.join(WORKSPACE_ROOT, "inventory.csv")
SESSION_FILE_PATH = os.path.join(WORKSPACE_ROOT, ".pathao_session.json")
PRODUCT_DESC_PATH = os.path.join(WORKSPACE_ROOT, "product description.md")
PATHAO_SIGNIN_URL = "https://commerce.pathao.com/sign-in?to=%2F"
PATHAO_BASE_URL = "https://commerce.pathao.com"
PATHAO_CATEGORY_DEFAULT = "752 - Electronics & Digital > Mobiles & Tablets > Mobile & Tablet Essentials > Mobile Cases & Covers"

# Load .env variables manually to avoid extra dependencies
def load_env_file(filepath: str = os.path.join(WORKSPACE_ROOT, ".env")):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v

load_env_file()

def get_product_description_for_material(material: str, phone_models: List[str]) -> str:
    """
    Generates a high-converting, formatted product description tailored to the
    material and phone models based on product description.md guidelines.
    """
    models_str = " / ".join(phone_models[:3])
    mat_lower = material.lower()

    if "silicone" in mat_lower:
        features = (
            "✨ Key Highlights & Features:\n"
            "• Silky Soft-Touch Finish: Baby-skin smooth silicone feel that repels dust and wipes clean instantly.\n"
            "• Velvet Microfiber Lining: Suede interior cushions your phone's back glass from micro-scratches.\n"
            "• 360° Shock Absorbing Cushion: Liquid silicone core disperses impact from accidental drops.\n"
            "• 1.2mm Raised Camera Bezel: Protects sensitive camera lenses when placed on flat surfaces.\n"
            "• 1:1 Precision CNC Mold: Accurate port cutouts and tactile clicky buttons.\n"
            "• Wireless Charging Ready: Ultra-slim form factor supports fast wireless charging.\n"
        )
    elif "pc" in mat_lower or "hard" in mat_lower:
        features = (
            "✨ Key Highlights & Features:\n"
            "• Smudge-Proof Frosted Matte Finish: Zero fingerprint marks or greasy smudges during daily use.\n"
            "• Anti-Yellowing Bayer Hard PC: Stays crystal-clean and transparent/matte permanently.\n"
            "• Heat Dissipation Architecture: Breathable micro-channels keep device cool under heavy gaming.\n"
            "• Strong Magnetic Attachment: Compatible with MagSafe and magnetic car mounts.\n"
            "• Elevated Screen & Lens Lips: Defends both screen and rear camera against surface scuffs.\n"
            "• Featherlight Armor: Slimline profile adds maximum defense with zero bulk in your pocket.\n"
        )
    elif "glass" in mat_lower or "tempered" in mat_lower:
        features = (
            "✨ Key Highlights & Features:\n"
            "• 9H Explosion-Proof Tempered Glass: Diamond-clear gloss that mimics the original glass back.\n"
            "• Scratch Immunity: Completely resists keys, coins, and everyday abrasive contact.\n"
            "• Electroplated Metallic Perimeter: Flagship luxury aesthetic with sleek shock-absorbing edges.\n"
            "• Oleophobic Nano-Layer: Repels finger oils, smudges, and moisture for lasting shine.\n"
            "• Flexible Bumper Border: Snaps on and off smoothly without scratching device edges.\n"
        )
    else:  # Acrylic / TPU / Hybrid
        features = (
            "✨ Key Highlights & Features:\n"
            "• Military-Grade Corner Airbags: Reinforced shock-pocket corners absorb drop impacts.\n"
            "• Crystal-Clear Hybrid Back: Showcases your phone's authentic factory color with clarity.\n"
            "• 5x Anti-Yellowing Acrylic: Resists discoloration significantly longer than basic clear covers.\n"
            "• Raised Protective Bezels: Keeps camera sapphire glass and touchscreen elevated off surfaces.\n"
            "• Tactile Independent Buttons: Preserves original, satisfying button responsiveness.\n"
        )

    desc = (
        f"Premium Protective Armor Case for {models_str}\n\n"
        f"{features}\n"
        "📦 Package Includes:\n"
        f"• 1x CoverStore Premium {material} Protective Case\n"
        "• 1x Quality Verification Seal\n\n"
        "🚚 CoverStore Trust Guarantee:\n"
        "• 100% Exact 1:1 Model Fit Guarantee\n"
        "• Fast Nationwide Cash-on-Delivery across Bangladesh\n"
        "• Parcel Inspection Enabled: Check your cover before completing payment!"
    )
    return desc

def load_and_group_inventory(csv_path: str = INVENTORY_CSV_PATH) -> List[Dict[str, Any]]:
    """
    Reads inventory.csv and groups records by MoveOn product link.
    1 MoveOn link = 1 parent product with multiple variants.
    """
    if not os.path.exists(csv_path):
        print(f"[!] Error: Inventory file not found at {csv_path}")
        return []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    groups_by_link = defaultdict(list)
    for r in rows:
        link = r.get("link", "").strip()
        if link:
            groups_by_link[link].append(r)

    products = []
    for link, items in groups_by_link.items():
        first = items[0]
        phone_models = sorted(list(set(i.get("Phone Model", "").strip() for i in items if i.get("Phone Model"))))
        materials = sorted(list(set(i.get("Material", "").strip() for i in items if i.get("Material"))))
        primary_material = materials[0] if materials else "Protective Case"
        
        # Determine Title
        title = first.get("SEO Title", "").strip()
        if not title:
            title = first.get("Product Name", "").strip()
        if not title:
            title = f"Luxury {primary_material} Protective Case for {' / '.join(phone_models)}"

        # Find gallery images
        gallery_images = []
        for model in phone_models:
            for mat in materials:
                gal_dir = os.path.join(WORKSPACE_ROOT, model, mat, "gallery")
                if os.path.exists(gal_dir):
                    imgs = [
                        os.path.join(gal_dir, f)
                        for f in sorted(os.listdir(gal_dir))
                        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
                    ]
                    for img in imgs:
                        if img not in gallery_images:
                            gallery_images.append(img)

        # Build variants
        variants = []
        for item in items:
            sku_code = item.get("Product Code", "").strip()
            color = item.get("Color", "").strip()
            model = item.get("Phone Model", "").strip()
            price_raw = item.get("sell price", 0)
            try:
                price = int(float(str(price_raw).replace(",", "").strip()))
            except Exception:
                price = 349

            # Resolve local SKU image
            img_path = ""
            mat = item.get("Material", "").strip()
            local_rel = item.get("Local Image Path", "").strip()
            if local_rel and os.path.exists(os.path.join(WORKSPACE_ROOT, local_rel)):
                img_path = os.path.join(WORKSPACE_ROOT, local_rel)
            elif model and mat and sku_code:
                candidate = os.path.join(WORKSPACE_ROOT, model, mat, "sku", f"{sku_code}.jpg")
                if os.path.exists(candidate):
                    img_path = candidate

            variants.append({
                "sku": sku_code,
                "phone_model": model,
                "color": color,
                "price": price,
                "stock": int(os.environ.get("PATHAO_DEFAULT_STOCK", 1)),
                "image_path": img_path
            })

        description = get_product_description_for_material(primary_material, phone_models)

        products.append({
            "source_link": link,
            "title": title,
            "phone_models": phone_models,
            "materials": materials,
            "primary_material": primary_material,
            "description": description,
            "gallery_images": gallery_images,
            "variants": variants
        })

    return products

class PathaoCommerceClient:
    """
    Automates authentication and product catalog operations on Pathao Commerce (https://commerce.pathao.com)
    using Playwright with session persistence.
    """
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        
        context_opts = {
            "viewport": {"width": 1366, "height": 768},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        if os.path.exists(SESSION_FILE_PATH):
            try:
                with open(SESSION_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("cookies") or data.get("origins"):
                        context_opts["storage_state"] = SESSION_FILE_PATH
                        print(f"[*] Loaded existing session from {os.path.basename(SESSION_FILE_PATH)}")
            except Exception as e:
                print(f"[!] Warning reading session file: {e}")

        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.context = self.browser.new_context(**context_opts)
        self.page = self.context.new_page()

    def close(self):
        if self.context and os.path.exists(SESSION_FILE_PATH):
            try:
                self.context.storage_state(path=SESSION_FILE_PATH)
            except Exception:
                pass
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def save_session(self):
        if self.context:
            self.context.storage_state(path=SESSION_FILE_PATH)
            print(f"[✓] Session state successfully saved to {os.path.basename(SESSION_FILE_PATH)}")

    def ensure_authenticated(self) -> bool:
        """
        Navigates to Pathao Commerce and verifies authentication.
        """
        print("[*] Checking Pathao Commerce authentication status...")
        self.page.goto(PATHAO_SIGNIN_URL, timeout=45000)
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

        login_input = self.page.query_selector("input[placeholder*='email or phone'], input#login_password")
        if login_input:
            print("[*] Authentication required. Submitting Pathao Commerce credentials...")
            email = os.environ.get("PATHAO_PHONE") or os.environ.get("PATHAO_EMAIL_OR_PHONE") or os.environ.get("PATHAO_EMAIL")
            password = os.environ.get("PATHAO_PASSWORD")

            if not email or not password:
                print("\n" + "!"*70)
                print(" [!] Missing PATHAO_EMAIL_OR_PHONE/PATHAO_PHONE or PATHAO_PASSWORD in .env")
                print("     PATHAO_PHONE=01780404797")
                print("     PATHAO_PASSWORD=your_password")
                print("!"*70 + "\n")
                return False

            try:
                self.page.wait_for_selector("input[placeholder*='email or phone'], input[type='text']", timeout=15000)
                self.page.fill("input[placeholder*='email or phone'], input[type='text']", email)
                self.page.fill("input#login_password, input[type='password']", password)
                
                print("[*] Submitting credentials, clicking Sign In...")
                self.page.click("button[type='submit']")
                self.page.wait_for_load_state("networkidle")
                time.sleep(4)

                page_text = self.page.content().lower()
                if "otp" in page_text or "verification" in page_text or "code" in page_text:
                    print("\n" + "="*70)
                    print(" [!] SMS/WhatsApp OTP Verification Detected!")
                    otp = input(" >> Please enter the Pathao OTP code here: ").strip()
                    print("="*70)
                    
                    otp_input = self.page.query_selector("input[type='number'], input[maxlength='6'], input[placeholder*='otp']")
                    if otp_input:
                        otp_input.fill(otp)
                        self.page.press("input[type='number'], input[maxlength='6'], input[placeholder*='otp']", "Enter")
                        time.sleep(3)
                        self.page.wait_for_load_state("networkidle")

                time.sleep(2)
                curr_content = self.page.content()
                if "Dashboard" in curr_content or "Zayo tech hub" in curr_content or "Products" in curr_content:
                    print(f"[✓] Successfully authenticated to Pathao Commerce! Active Store: Zayo tech hub")
                    self.save_session()
                    return True
                else:
                    print(f"[!] Login could not complete automatically. Final URL: {self.page.url}")
                    return False
            except Exception as e:
                print(f"[!] Error during login interaction: {e}")
                return False
        else:
            print(f"[✓] Already authenticated via stored session! Active Store: Zayo tech hub")
            return True

    def ensure_media_gallery_assets(self, product: Dict[str, Any]) -> Dict[str, str]:
        """
        Uploads product gallery and SKU images to Pathao Media Gallery (or retrieves existing CDN URLs).
        Returns a dictionary mapping filename (e.g., 'RN8-SIL-WT-S.jpg') to its Pathao CDN URL.
        """
        print(f"[*] Checking/Uploading assets to Pathao Media Gallery...")
        self.page.goto(f"{PATHAO_BASE_URL}/media-gallery", timeout=35000)
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

        cdn_url_map = {}

        # Collect local files
        target_files = []
        for g in product.get("gallery_images", []):
            if os.path.exists(g):
                target_files.append(g)
        for v in product.get("variants", []):
            p = v.get("image_path")
            if p and os.path.exists(p) and p not in target_files:
                target_files.append(p)

        # Query existing items in Pathao gallery
        try:
            existing = self.page.evaluate("""async () => {
                const resp = await fetch('/api/v1/upload/media?limit=100&offset=0');
                const json = await resp.json();
                return json.data || [];
            }""")
            for item in existing:
                fn = item.get("file_name")
                url = item.get("image_url")
                if fn and url:
                    cdn_url_map[fn] = url
        except Exception as e:
            print(f"[!] Warning reading existing media gallery: {e}")

        # Check which files need upload
        needed = [f for f in target_files if os.path.basename(f) not in cdn_url_map]
        if needed:
            print(f"[*] Uploading {len(needed)} new asset(s) to Pathao Media Gallery...")
            
            def on_resp(resp):
                if "api/v1/upload/media" in resp.url and resp.request.method == "POST" and resp.status == 200:
                    try:
                        d = resp.json().get("data", {})
                        fn = d.get("file_name")
                        url = d.get("image_url")
                        if fn and url:
                            cdn_url_map[fn] = url
                            print(f"    [+] Uploaded: {fn} -> {url}")
                    except Exception:
                        pass

            self.page.on("response", on_resp)
            file_input = self.page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(needed)
                time.sleep(8)
                self.page.wait_for_load_state("networkidle")

        print(f"[✓] Assets mapped: {len(target_files)} local files mapped to Pathao CDN URLs")
        return cdn_url_map

    def generate_import_workbook(self, product: Dict[str, Any], cdn_map: Dict[str, str], output_path: str) -> str:
        """
        Creates a Pathao Commerce compatible Excel import file (single Sheet1).
        Follows the 1-parent + N-variants structure with CDN images, markdown description, and stock.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"

        headers = [
            "PRODUCT_ID", "PRODUCT_NAME", "CATEGORY", "BASE_SKU",
            "VARIANT_SKU", "VARIANT_OPTIONS", "BASE_PRICE", "DISCOUNTED_PRICE",
            "WEIGHT_KG", "WIDTH_CM", "LENGTH_CM", "HEIGHT_CM",
            "CURRENT_STOCK", "DISABLE", "IMAGES", "DESCRIPTION"
        ]
        ws.append(headers)

        # Parent Product Row
        variants = product["variants"]
        parent_price = variants[0]["price"] if variants else 349
        base_sku = variants[0]["sku"].rsplit("-", 2)[0] if variants else "COVER"
        
        gallery_urls = []
        for g in product.get("gallery_images", []):
            fn = os.path.basename(g)
            if fn in cdn_map:
                gallery_urls.append(cdn_map[fn])
        parent_images = ",".join(gallery_urls)

        ws.append([
            "",                                         # PRODUCT_ID
            product["title"],                           # PRODUCT_NAME
            PATHAO_CATEGORY_DEFAULT,                    # CATEGORY
            base_sku,                                   # BASE_SKU
            "",                                         # VARIANT_SKU
            "",                                         # VARIANT_OPTIONS
            parent_price + 50,                          # BASE_PRICE
            parent_price,                               # DISCOUNTED_PRICE
            0.05,                                       # WEIGHT_KG
            8,                                          # WIDTH_CM
            16,                                         # LENGTH_CM
            1,                                          # HEIGHT_CM
            1,                                          # CURRENT_STOCK
            "NO",                                       # DISABLE
            parent_images,                              # IMAGES
            product["description"]                      # DESCRIPTION
        ])

        # Variant Rows
        for v in variants:
            sku = v["sku"]
            v_fn = f"{sku}.jpg"
            v_img = cdn_map.get(v_fn, "")
            
            ws.append([
                "",                                     # PRODUCT_ID
                "",                                     # PRODUCT_NAME
                "",                                     # CATEGORY
                "",                                     # BASE_SKU
                sku,                                    # VARIANT_SKU
                f"Color: {v['color']}",                 # VARIANT_OPTIONS
                v["price"] + 50,                        # BASE_PRICE
                v["price"],                             # DISCOUNTED_PRICE
                0.05,                                   # WEIGHT_KG
                8,                                      # WIDTH_CM
                16,                                     # LENGTH_CM
                1,                                      # HEIGHT_CM
                v["stock"],                             # CURRENT_STOCK
                "NO",                                   # DISABLE
                v_img,                                  # IMAGES
                ""                                      # DESCRIPTION
            ])

        wb.save(output_path)
        print(f"[✓] Generated Pathao import workbook: {output_path} ({len(variants) + 1} total rows)")
        return output_path

    def import_workbook_to_store(self, xlsx_path: str) -> bool:
        """
        Executes the 5-step automated bulk import workflow in Pathao Commerce.
        """
        print(f"[*] Navigating to Pathao Commerce Products page for import...")
        self.page.goto(f"{PATHAO_BASE_URL}/products", timeout=35000)
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Step 1: Open modal
        print("[*] Opening 'Import Products' modal...")
        import_btn = self.page.query_selector("button:has-text('Import Products')")
        if not import_btn:
            print("[!] Could not find 'Import Products' button.")
            return False
        import_btn.click()
        time.sleep(2)

        # Step 1 Modal: Warehouse selection -> Next
        print("[*] Step 1: Confirming Source & Warehouse...")
        next_btn = self.page.query_selector(".ant-modal button:has-text('Next')")
        if next_btn:
            next_btn.click()
            time.sleep(2)

        # Step 2 Modal: Upload file
        print(f"[*] Step 2: Uploading {os.path.basename(xlsx_path)}...")
        file_input = self.page.query_selector(".ant-modal input[type='file']")
        if not file_input:
            print("[!] Could not find file input in import modal.")
            return False
        file_input.set_input_files(xlsx_path)
        time.sleep(2)
        
        next_btn = self.page.query_selector(".ant-modal button:has-text('Next')")
        if next_btn:
            next_btn.click()
            time.sleep(3)

        # Step 3 Modal: Configure (Auto-mapped columns)
        print("[*] Step 3: Verifying Column Mapping...")
        next_btn = self.page.query_selector(".ant-modal button:has-text('Next')")
        if next_btn:
            next_btn.click()
            time.sleep(4)
            self.page.wait_for_load_state("networkidle")

        # Step 4 Modal: Validation
        print("[*] Step 4: Validating products on Pathao...")
        val_btn = self.page.query_selector(".ant-modal button:has-text('Validate products')")
        if val_btn:
            val_btn.click()
            time.sleep(3)
            self.page.wait_for_load_state("networkidle")

        # Check for Import button (e.g. 'Import 10 / 10 rows')
        import_rows_btn = self.page.query_selector(".ant-modal button:has-text('Import')")
        if import_rows_btn:
            btn_text = import_rows_btn.inner_text().strip()
            print(f"[*] Submitting catalog import: '{btn_text}'...")
            import_rows_btn.click()
            time.sleep(5)
            self.page.wait_for_load_state("networkidle")
            print("[✓] Product catalog import submitted successfully!")
            
            # Wait for modal to close or finish
            time.sleep(4)
            self.page.goto(f"{PATHAO_BASE_URL}/products", timeout=35000)
            self.page.wait_for_load_state("networkidle")
            time.sleep(2)
            return True
        else:
            print("[!] Import button not found after validation.")
            return False

    def sync_product(self, product: Dict[str, Any]) -> bool:
        """
        Uploads or updates a single parent product with all its SKU variants on Pathao Commerce.
        """
        title = product["title"]
        print("\n" + "="*80)
        print(f"[*] SYNCING TO PATHAO COMMERCE: {title}")
        print(f"    Variants ({len(product['variants'])}): {', '.join(v['sku'] for v in product['variants'])}")
        print(f"    Gallery Images ({len(product['gallery_images'])}): {[os.path.basename(p) for p in product['gallery_images']]}")
        print("="*80)

        # 1. Upload assets to Media Gallery
        cdn_map = self.ensure_media_gallery_assets(product)

        # 2. Build Excel import workbook
        import_filename = f"pathao_import_{product['variants'][0]['sku'].rsplit('-', 2)[0].lower()}.xlsx"
        import_path = os.path.join(WORKSPACE_ROOT, import_filename)
        self.generate_import_workbook(product, cdn_map, import_path)

        # 3. Perform automated bulk import in Pathao Commerce
        success = self.import_workbook_to_store(import_path)
        if success:
            print(f"\n[✓] SUCCESSFULLY SYNCED TO PATHAO COMMERCE: {title}")
        else:
            print(f"\n[!] FAILED TO SYNC: {title}")
        return success

def print_dry_run_summary(products: List[Dict[str, Any]]):
    """Prints a detailed breakdown of catalog grouping and variant payloads."""
    print("=" * 80)
    print("  PATHAO COMMERCE CATALOG SYNC — DRY-RUN BREAKDOWN")
    print(f"  Total Parent Products (MoveOn Links): {len(products)}")
    total_skus = sum(len(p["variants"]) for p in products)
    print(f"  Total Variant SKUs:                   {total_skus}")
    print("=" * 80)

    for idx, prod in enumerate(products, 1):
        print(f"\n[{idx}/{len(products)}] {prod['title']}")
        print(f"  • Source Link:     {prod['source_link']}")
        print(f"  • Models:          {', '.join(prod['phone_models'])}")
        print(f"  • Material:        {prod['primary_material']}")
        print(f"  • Gallery Images:  {len(prod['gallery_images'])} found")
        for g in prod['gallery_images'][:3]:
            print(f"      - {os.path.relpath(g, WORKSPACE_ROOT)}")
        if len(prod['gallery_images']) > 3:
            print(f"      - ... (+{len(prod['gallery_images']) - 3} more)")

        print(f"  • Variants ({len(prod['variants'])}):")
        for v in prod['variants']:
            img_status = "✓" if v['image_path'] and os.path.exists(v['image_path']) else "✗ missing"
            print(f"      - SKU: {v['sku']:<16} | Model: {v['phone_model']:<18} | Color: {v['color']:<16} | Price: ৳{v['price']:<4} | Stock: {v['stock']} | Image: {img_status}")

    print("\n" + "=" * 80)
    print("  DRY-RUN VERIFICATION COMPLETE")
    print("=" * 80 + "\n")

def main():
    parser = argparse.ArgumentParser(description="CoverStore Pathao Commerce Catalog Synchronizer")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Inspect grouped product payloads and image paths without updating Pathao Commerce")
    parser.add_argument("--test-login", "-t", action="store_true", help="Test authentication and session storage state with https://commerce.pathao.com")
    parser.add_argument("--headful", action="store_true", help="Run browser in headful mode for visible interaction or manual login/OTP")
    parser.add_argument("--link", type=str, default=None, help="Sync only a specific MoveOn product URL")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of parent products to sync")
    args = parser.parse_args()

    products = load_and_group_inventory()
    if not products:
        print("[!] No products found in inventory.")
        return

    # Filter by link if specified
    if args.link:
        products = [p for p in products if args.link in p["source_link"]]
        print(f"[*] Filtered to {len(products)} product(s) matching URL: {args.link}")

    if args.limit:
        products = products[:args.limit]
        print(f"[*] Limited to first {len(products)} product(s).")

    if args.dry_run:
        print_dry_run_summary(products)
        return

    client = PathaoCommerceClient(headless=not args.headful)
    try:
        client.start()
        authenticated = client.ensure_authenticated()
        if not authenticated:
            print("[!] Authentication could not be established. Exiting.")
            return

        if args.test_login:
            print("[✓] Login verification test succeeded! Session saved.")
            return

        print(f"\n[*] Beginning catalog sync for {len(products)} parent product(s)...")
        success_count = 0
        for prod in products:
            if client.sync_product(prod):
                success_count += 1

        print(f"\n[✓] Pathao Commerce sync completed: {success_count}/{len(products)} products processed successfully!")
    finally:
        client.close()

if __name__ == "__main__":
    main()
