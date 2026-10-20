import os
import sys
import csv
import io
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPTS_DIR = os.path.abspath(os.path.dirname(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from moveon_client import MoveOnClient, extract_product_id_from_url
from sku_generator import generate_sku, disambiguate_sku, resolve_sku_collision

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INVENTORY_CSV_PATH = os.path.join(WORKSPACE_ROOT, "inventory.csv")
INVENTORY_XLSX_PATH = os.path.join(WORKSPACE_ROOT, "inventory.xlsx")
GOOGLE_SHEET_XLSX_URL = "https://docs.google.com/spreadsheets/d/1cfLya8zgGBLZfor3g7-ljrjw7lmo3J28uxkqiOONzhk/export?format=xlsx"

# 21-Column Financial & Listing Schema
FIELDNAMES = [
    "Product Code",       # A (1)
    "SEO Title",          # B (2)
    "Product Name",       # C (3)
    "Material",           # D (4)
    "Color",              # E (5)
    "Phone Model",        # F (6)
    "Warranty",           # F (7)
    "source link",        # H (8)
    "link",               # I (9)
    "Local Image Path",   # J (10)
    "product price",      # K (11)
    "china delivery",     # L (12)
    "air shipping",       # M (13)
    "bd delivery",        # N (14)
    "packaging",          # O (15)
    "printing",           # P (16)
    "other",              # Q (17)
    "landing cost",       # R (18)
    "margin",             # S (19)
    "sell price",         # T (20)
    "max discount"        # U (21)
]

NUMERIC_COST_FIELDS = [
    "product price",
    "china delivery",
    "air shipping",
    "bd delivery",
    "packaging",
    "printing",
    "other",
]

def clean_float(val: Any, default: float = 0.0) -> float:
    """Safely converts value to float, handling strings with commas, spaces, or currency symbols."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace(",", "").replace("$", "").replace("৳", "")
    if not val_str:
        return default
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return default

def load_existing_inventory(csv_path: str = INVENTORY_CSV_PATH) -> List[Dict[str, str]]:
    """Loads existing inventory rows from inventory.csv (UTF-8 BOM)."""
    if not os.path.exists(csv_path):
        return []
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []

def get_existing_skus(csv_path: str = INVENTORY_CSV_PATH) -> set:
    """Returns a set of all non-empty Product Code strings in inventory.csv."""
    rows = load_existing_inventory(csv_path)
    return {r.get("Product Code", "").strip() for r in rows if r.get("Product Code")}

def prompt_china_delivery(cli_val: Optional[float] = None) -> float:
    """
    Enforces Rule 9 Mandatory China Domestic Delivery Charge Standard:
    Never assume, hardcode, or silently default China domestic delivery charge.
    Requires explicit value or interactively prompts user.
    Raises ValueError if run non-interactively without explicit charge.
    """
    if cli_val is not None:
        val = clean_float(cli_val)
        if val < 0:
            raise ValueError(f"Invalid China domestic delivery charge: {cli_val}. Must be >= 0.")
        print(f"[✓] China domestic delivery charge applied: {val:.2f} BDT")
        return val

    # If running interactively, prompt the user
    if sys.stdin.isatty():
        print("\n" + "="*65)
        print(" [!] MANDATORY CHINA DOMESTIC DELIVERY CHARGE (Rule 9)")
        print("     Never assume, hardcode, or silently default logistics costs.")
        print("="*65)
        while True:
            try:
                raw_input = input("Enter exact China domestic delivery fee in BDT per unit: ").strip()
                if not raw_input:
                    print(" [!] Error: Delivery fee cannot be empty. Please enter a valid number (e.g. 10.0, 15.0).")
                    continue
                val = float(raw_input)
                if val < 0:
                    print(" [!] Error: Delivery fee cannot be negative.")
                    continue
                return val
            except ValueError:
                print(" [!] Error: Invalid numeric input. Please enter a valid float (e.g. 10.0).")
            except (EOFError, KeyboardInterrupt):
                raise ValueError("Mandatory China domestic delivery charge prompt was cancelled.")
    else:
        raise ValueError(
            "Mandatory China domestic delivery charge (Rule 9) is required. "
            "When running non-interactively or in automated pipelines, provide --china-delivery <BDT>."
        )

def calculate_landing_cost(product_price: float, china_del: float, air_ship: float, bd_del: float, packaging: float = 11.5, printing: float = 20.0, other: float = 0.0) -> float:
    """Calculates landing cost as the sum of product price and all logistics/overhead expenses."""
    return round(clean_float(product_price) + clean_float(china_del) + clean_float(air_ship) + clean_float(bd_del) + clean_float(packaging, 11.5) + clean_float(printing, 20.0) + clean_float(other, 0.0), 2)

def calculate_margin(landing_cost: float) -> float:
    """
    Calculates dynamic margin markup:
    - If landing cost < 300: 40% markup (cost * 1.40)
    - If landing cost < 400: 33% markup (cost * 1.33)
    - If landing cost >= 400: 25% markup (cost * 1.25)
    """
    lc = float(landing_cost or 0.0)
    if lc < 300:
        return round(lc * 1.40, 2)
    elif lc < 400:
        return round(lc * 1.33, 2)
    else:
        return round(lc * 1.25, 2)

def calculate_sell_price(margin_cost: float) -> int:
    """
    Calculates final sell price by rounding based on the last 2 digits of the margin integer:
    - Last 2 digits < 25: ends in 00 (e.g. 320 -> 300)
    - Last 2 digits 25 to 74: ends in 49 (e.g. 345 -> 349)
    - Last 2 digits 75 to 99: ends in 99 (e.g. 385 -> 399)
    """
    int_val = int(round(float(margin_cost or 0.0)))
    base = (int_val // 100) * 100
    rem = int_val % 100
    if rem < 25:
        return base
    elif rem <= 74:
        return base + 49
    else:
        return base + 99

def calculate_max_discount(sell_price: int) -> float:
    """
    Calculates max discount using user formula:
    =IF(sell_price < 300, 0, MIN(99, IF(sell_price < 500, sell_price * 7%, IF(sell_price < 700, sell_price * 12%, sell_price * 15%))))
    """
    sp = float(sell_price or 0.0)
    if sp < 300:
        return 0.0
    if sp < 500:
        d = sp * 0.07
    elif sp < 700:
        d = sp * 0.12
    else:
        d = sp * 0.15
    return min(99.0, round(d, 2))

def generate_seo_title(product_name: str, phone_model: str, material: str) -> str:
    """
    Generates a high-converting, SEO-optimized Daraz Bangladesh title
    highlighting key selling points, phone model, and materials.
    """
    pn = (product_name or "").lower()
    pm = (phone_model or "").strip()
    mat = (material or "").lower()

    # Realme Neo8 / Neo7 Heat Dissipation Hard PC
    if "neo8" in pm.lower() and ("pc" in mat or "heat" in pn or "dissipation" in pn):
        return "Magnetic Heat Dissipation Matte Back Cover for Realme GT Neo 8 / Neo 7 – Ultra Thin Breathable Cooling Case with Ring Magnet"

    # Realme Neo8 Graphene Cooling Silicone
    if "neo8" in pm.lower() and ("graphene" in pn or "cooling" in pn or "airbag" in pn or ("silicone" in mat and "liquid" not in mat)):
        return "Magnetic Graphene Cooling Silicone Case for Realme GT Neo 8 – Snowflake Heat Dissipation Airbag Anti-Drop Back Cover"

    # Realme Neo8 Liquid Silicone
    if "neo8" in pm.lower() and "silicone" in mat:
        return "Luxury Liquid Silicone Shockproof Case for Realme GT Neo 8 – Skin-Friendly Soft Cube Anti-Drop Protective Back Cover"

    # Realme Neo8 TPU Magnetic
    if "neo8" in pm.lower() and "tpu" in mat:
        return "Magnetic Ultra-Thin Shockproof Case for Realme GT Neo 8 – Slim Soft TPU Full Protection Back Cover"

    # Honor 600 Lite / Honor X80i Hard PC
    if ("600lite" in pm.lower() or "600 lite" in pm.lower() or "x80i" in pm.lower()) and "pc" in mat:
        return "Micro-Matte Magnetic Shockproof Case for Honor 600 Lite / Honor X80i – Ultra-Slim Hard Protective Back Cover"

    # Honor 600 Lite Silicone (Moiré)
    if ("600lite" in pm.lower() or "600 lite" in pm.lower()) and "silicone" in mat:
        return "Magnetic Liquid Silicone Case for Honor 600 Lite – Moiré Texture Anti-Scratch Soft Protective Back Cover"

    # Honor X80i TPU with Stand / Airbag
    if ("x80" in pm.lower() or "x70" in pn or "x60" in pn) and ("stand" in pn or "airbag" in pn or "tpu" in mat):
        return "Invisible Kickstand Airbag Shockproof Case for Honor X80i / X70 / X60 Pro – Clear Hybrid TPU Protective Back Cover"

    # Honor 600 / 600 Pro Skin
    if "honor 600" in pm.lower() and "skin" in mat:
        return f"Ultra-Thin Matte Skin Protective Case for {pm} – Lightweight Anti-Fingerprint Back Cover"

    # Samsung Galaxy S26 Ultra
    if "s26" in pm.lower() or "s24" in pm.lower() or "galaxy" in pm.lower():
        if "spider" in pn:
            return f"3D Spider Style Shockproof Silicone Case for {pm} – Printed Anti-Drop Protective Back Cover"
        elif "bracket" in pn or "frame" in mat or "acrylic" in mat:
            return f"Magnetic Invisible Stand Armor Case for {pm} – Heavy Duty Metal Lens Frame Hybrid Back Cover"
        elif "wood" in pn or "wood" in mat or "pcs" in mat:
            return f"Luxury Wood Grain Magnetic Case for {pm} – Slim Shockproof Hard Back Cover"
        else:
            return f"Luxury Magnetic Shockproof Protective Case for {pm} – Premium Armor Back Cover"

    # iPhone Models
    if "iphone" in pm.lower():
        if "tpu" in mat:
            return f"Magnetic Clear Shockproof TPU Case with Lens Film for {pm} – Full Protection Slim Soft Cover"
        elif "acrylic" in mat or "acrylic" in pn:
            return f"Luxury Magnetic Clear Acrylic Case for {pm} – Anti-Yellow Shockproof Hard Hybrid Back Cover"
        elif "lens" in pn or "film" in pn or "pcs" in mat:
            return f"Ultra-Slim Matte Hard Case with Camera Lens Protector for {pm} – Luxury Anti-Scratch Protective Back Cover"
        else:
            return f"Luxury Magnetic Shockproof Protective Case for {pm} – Slim Armor Back Cover"

    # Redmi Turbo 4 / Turbo 4 Pro
    if "turbo" in pm.lower() or "redmi" in pm.lower():
        if "glass" in mat or "glass" in pn:
            return f"Luxury 9H Tempered Glass Back Cover for {pm} – Glossy Anti-Scratch Armor Protective Case"
        elif "mecha" in pn or "acrylic" in mat:
            return f"Mecha Armor Shockproof Matte Case for {pm} – Heavy Duty Acrylic Bumper Back Cover"
        else:
            return f"Shockproof Matte Protective Back Cover for {pm} – Slim Armor Case"

    # Generic Fallback
    mat_clean = material.replace("PCs", "Hard PC").strip()
    return f"Luxury {mat_clean} Shockproof Protective Back Cover for {pm} – Ultra-Slim Anti-Drop Case"

def fetch_live_google_sheet_data() -> List[Dict[str, Any]]:
    """
    Downloads the full Google Sheet workbook as XLSX and merges metadata from Sheet1
    with existing cost data from the inventory tab.
    """
    req = urllib.request.Request(GOOGLE_SHEET_XLSX_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
            wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
            s1 = wb['Sheet1'] if 'Sheet1' in wb.sheetnames else wb.active
            inv_tab = wb['inventory'] if 'inventory' in wb.sheetnames else None

            s1_headers = [str(s1.cell(1, col).value or '').strip() for col in range(1, s1.max_column + 1)]
            
            rows = []
            for r in range(2, s1.max_row + 1):
                name_val = s1.cell(r, 1).value
                if not name_val:
                    continue
                
                row_dict: Dict[str, Any] = {}
                for c_idx, h in enumerate(s1_headers, 1):
                    row_dict[h] = str(s1.cell(r, c_idx).value or '').strip()

                sku_code = row_dict.get("Product Code", "")
                phone_model = row_dict.get("Phone Model", "")
                material = row_dict.get("Material", "")

                # Ensure SEO Title is populated
                if not row_dict.get("SEO Title"):
                    row_dict["SEO Title"] = generate_seo_title(row_dict.get("Product Name", ""), phone_model, material)

                # Check if local image path exists
                local_img = ""
                if phone_model and material and sku_code:
                    potential_path = os.path.join(WORKSPACE_ROOT, phone_model, material, "sku", f"{sku_code}.jpg")
                    if os.path.exists(potential_path):
                        local_img = f"{phone_model}/{material}/sku/{sku_code}.jpg"
                row_dict["Local Image Path"] = local_img

                # Default costs
                prod_price = 0.0
                china_del = 10.0
                air_ship = 50.0
                bd_del = 5.0
                packaging = 11.5
                printing = 20.0
                other = 0.0

                # Extract existing costs from inventory tab if present
                if inv_tab and r <= inv_tab.max_row:
                    try:
                        p_val = inv_tab.cell(r, 3).value
                        c_val = inv_tab.cell(r, 5).value
                        a_val = inv_tab.cell(r, 6).value
                        b_val = inv_tab.cell(r, 7).value
                        o_val = inv_tab.cell(r, 10).value
                        if p_val is not None:
                            prod_price = round(float(p_val), 2)
                        if c_val is not None:
                            china_del = round(float(c_val), 2)
                        if a_val is not None:
                            air_ship = round(float(a_val), 2)
                        if b_val is not None:
                            bd_del = round(float(b_val), 2)
                        if o_val is not None:
                            other = round(float(o_val), 2)
                    except Exception:
                        pass

                row_dict["product price"] = prod_price
                row_dict["china delivery"] = china_del
                row_dict["air shipping"] = air_ship
                row_dict["bd delivery"] = bd_del
                row_dict["packaging"] = packaging
                row_dict["printing"] = printing
                row_dict["other"] = other

                # Calculate landing cost, margin, sell price, max discount
                landing = calculate_landing_cost(prod_price, china_del, air_ship, bd_del, packaging, printing, other)
                margin_val = calculate_margin(landing)
                sell_p = calculate_sell_price(margin_val)
                max_d = calculate_max_discount(sell_p)

                row_dict["landing cost"] = landing
                row_dict["margin"] = margin_val
                row_dict["sell price"] = sell_p
                row_dict["max discount"] = max_d

                rows.append(row_dict)

            return rows
    except Exception as e:
        print(f"[!] Warning: Could not fetch live Google Sheet workbook: {e}")
        return []

def save_to_csv(rows: List[Dict[str, Any]], filepath: str = INVENTORY_CSV_PATH):
    """Saves inventory rows to CSV with UTF-8 BOM encoding."""
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            clean_row = {k: r.get(k, "") for k in FIELDNAMES}
            writer.writerow(clean_row)
    print(f"[+] Successfully saved {len(rows)} records to CSV: {filepath}")

def save_to_excel(rows: List[Dict[str, Any]], filepath: str = INVENTORY_XLSX_PATH):
    """Saves inventory rows to styled Excel workbook with live formulas for pricing columns."""
    wb = openpyxl.Workbook()
    wb.calculation.calcMode = 'auto'
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    ws = wb.active
    ws.title = "Sheet1"

    # Style definitions
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    data_font = Font(name="Calibri", size=10)
    alt_fill = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # Write Header
    ws.append(FIELDNAMES)
    for col_idx in range(1, len(FIELDNAMES) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # Write Data Rows
    for row_idx, r in enumerate(rows, 2):
        row_vals = []
        for k in FIELDNAMES:
            if k == "landing cost":
                row_vals.append(f"=SUM(K{row_idx}:Q{row_idx})")
            elif k == "margin":
                row_vals.append(f"=IF(R{row_idx}<300, R{row_idx}*1.4, IF(R{row_idx}<400, R{row_idx}*1.33, R{row_idx}*1.25))")
            elif k == "sell price":
                row_vals.append(f"=INT(S{row_idx}/100)*100 + IF(MOD(ROUND(S{row_idx},0),100)<25, 0, IF(MOD(ROUND(S{row_idx},0),100)<=74, 49, 99))")
            elif k == "max discount":
                row_vals.append(f"=IF(T{row_idx}<300, 0, MIN(99, IF(T{row_idx}<500, T{row_idx}*7%, IF(T{row_idx}<700, T{row_idx}*12%, T{row_idx}*15%))))")
            elif k in NUMERIC_COST_FIELDS:
                row_vals.append(clean_float(r.get(k)))
            else:
                row_vals.append(str(r.get(k, "") or ""))

        ws.append(row_vals)
        use_alt = (row_idx % 2 == 0)
        
        for col_idx in range(1, len(FIELDNAMES) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = thin_border
            if use_alt:
                cell.fill = alt_fill

            field_name = FIELDNAMES[col_idx - 1]
            if field_name in ["product price", "china delivery", "air shipping", "bd delivery", "packaging", "printing", "other", "landing cost", "margin", "max discount"]:
                cell.alignment = right_align
                cell.number_format = "#,##0.00"
            elif field_name == "sell price":
                cell.alignment = right_align
                cell.number_format = "#,##0"
            elif field_name in ["Product Code", "Material", "Color", "Phone Model", "Warranty", "source link"]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

    # Freeze header row
    ws.freeze_panes = "A2"

    # Auto-adjust column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        col_name = str(ws.cell(row=1, column=col[0].column).value or '')
        if col_name in ["landing cost", "margin", "sell price", "max discount"]:
            ws.column_dimensions[col_letter].width = 16
            continue
        max_len = 0
        for cell in col:
            val = cell.value
            if val is None:
                continue
            val_str = str(val)
            if val_str.startswith('='):
                continue
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)

    # Save handling file locks gracefully
    saved = False
    for attempt in range(2):
        try:
            wb.save(filepath)
            print(f"[+] Successfully saved {len(rows)} records to Excel: {filepath}")
            saved = True
            break
        except PermissionError:
            if attempt == 0:
                print(f"[!] Notice: '{os.path.basename(filepath)}' is locked (likely open in Excel). Retrying in 2 seconds...")
                import time
                time.sleep(2)
            else:
                alt_path = os.path.splitext(filepath)[0] + "_updated.xlsx"
                try:
                    wb.save(alt_path)
                    print(f"[!] Notice: '{os.path.basename(filepath)}' is currently open in Excel. Saved updated copy to '{os.path.basename(alt_path)}'.")
                except Exception as e:
                    print(f"[!] Warning: Could not save Excel file: {e}")

def sync_inventory():
    """Performs full sync: live sheet + historical cost preservation + Realme Neo8 append."""
    print("[*] Fetching live Google Sheet rows and historical costs...")
    enriched_rows = fetch_live_google_sheet_data()
    print(f"    Loaded {len(enriched_rows)} rows from live Google Sheet.")

    # Fetch Realme Neo8 product data to append
    rn8_url = "https://moveon.global/BD_en/products/0000000MJPDSKGCI-suitable-for-realme-neo8-phone-case-simple-solid-color-cube-liquid-silicone-full-cover-anti-drop-soft-case-new-model/1AD8354574484115"
    client = MoveOnClient()
    try:
        rn8_data = client.fetch_product(rn8_url)
        title = rn8_data["title"]
        material = "Liquid Silicone"
        model_name = "Realme Neo8"
        skus_by_model = rn8_data.get("skus_by_model", {}).get(model_name, [])

        print(f"[*] Appending {len(skus_by_model)} Realme Neo8 SKUs...")
        for idx, sku in enumerate(skus_by_model):
            variant_label = sku.get("variant_label", "")
            sku_code = generate_sku(model_name, material, variant_label, title)
            
            # Clean color name
            color_name = variant_label
            for prefix in ["Straight Edge New Model [", "Rubik's Cube Liquid Silicone", "]"]:
                color_name = color_name.replace(prefix, "")
            color_name = color_name.strip()

            price_dict = sku.get("price", {})
            dropship = price_dict.get("dropship", {})
            price_val = dropship.get("offer_price") or price_dict.get("original") or 34.0935
            
            # Wholesale BDT price (MoveOn dropship/offer price is natively in BDT)
            prod_price = round(float(price_val), 2)
            china_del = 10.0
            air_ship = 50.0
            bd_del = 5.0
            packaging = 11.5
            printing = 20.0
            other = 0.0

            landing = calculate_landing_cost(prod_price, china_del, air_ship, bd_del, packaging, printing, other)
            margin_val = calculate_margin(landing)
            sell_p = calculate_sell_price(margin_val)
            max_d = calculate_max_discount(sell_p)

            local_path = f"Realme Neo8/Liquid Silicone/sku/{sku_code}.jpg"

            new_row = {
                "Product Code": sku_code,
                "SEO Title": generate_seo_title(title, model_name, material),
                "Product Name": title,
                "Material": material,
                "Color": color_name,
                "Phone Model": model_name,
                "Warranty": "No",
                "source link": "Link",
                "link": rn8_url,
                "Local Image Path": local_path,
                "product price": prod_price,
                "china delivery": china_del,
                "air shipping": air_ship,
                "bd delivery": bd_del,
                "packaging": packaging,
                "printing": printing,
                "other": other,
                "landing cost": landing,
                "margin": margin_val,
                "sell price": sell_p,
                "max discount": max_d
            }
            enriched_rows.append(new_row)
    except Exception as e:
        print(f"[!] Error appending Realme Neo8 data: {e}")

    # Save to CSV and XLSX
    save_to_csv(enriched_rows)
    save_to_excel(enriched_rows)
    print(f"\n[✓] Inventory synchronization complete! Total rows: {len(enriched_rows)}")

def append_downloaded_product(
    product_info: Dict[str, Any],
    selected_models: List[Dict[str, str]],
    material: str,
    product_url: str,
    china_del: Optional[float] = None,
    air_ship: Optional[float] = None,
    bd_del: float = 5.0,
    packaging: float = 11.5,
    printing: float = 20.0,
    other: float = 0.0
):
    """
    Appends newly downloaded product variants into inventory.csv and inventory.xlsx using 21-column schema.
    Mandatory China domestic delivery charge is enforced per Rule 9.
    """
    if china_del is None:
        china_del = prompt_china_delivery()
    else:
        china_del = clean_float(china_del)

    title = product_info.get("title", "")
    skus_by_model = product_info.get("skus_by_model", {})

    existing_rows = []
    existing_codes = set()
    if os.path.exists(INVENTORY_CSV_PATH):
        try:
            with open(INVENTORY_CSV_PATH, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    existing_rows.append(r)
                    code = r.get("Product Code", "").strip()
                    if code:
                        existing_codes.add(code)
        except Exception:
            pass

    new_rows = []
    updated_count = 0
    for model_meta in selected_models:
        model_name = model_meta["clean_name"]
        model_skus = skus_by_model.get(model_name, [])
        if not model_skus and len(selected_models) == 1:
            for v in skus_by_model.values():
                model_skus.extend(v)

        for sku in model_skus:
            variant_label = sku.get("variant_label", "")
            if sku.get("resolved_sku"):
                sku_code = sku["resolved_sku"]
            else:
                base_code = generate_sku(model_name, material, variant_label, title)
                if base_code in existing_codes:
                    sku_code = resolve_sku_collision(base_code, existing_codes, variant_label=variant_label, interactive=False)
                else:
                    sku_code = base_code
            existing_codes.add(sku_code)

            color_name = variant_label
            bracket_match = re.search(r'\[([^\]]+)\]', color_name)
            if bracket_match:
                color_name = bracket_match.group(1).title()
            else:
                for prefix in ["Straight Edge New Model [", "Rubik's Cube Liquid Silicone", "Built-in magnetic tpu frosted soft shell", "Built-in magnetic suction - ", "Built-in magnetic suction-", "anti-fingerprint - skin-friendly", "]"]:
                    color_name = color_name.replace(prefix, "")
                color_name = color_name.strip(" []-").title()

            price_dict = sku.get("price", {})
            dropship = price_dict.get("dropship", {})
            price_val = dropship.get("offer_price") or price_dict.get("original") or 34.0935
            prod_price = round(float(price_val), 2)
            # Extract SKU weight and compute air shipping: weight * 2 * 780 BDT/kg
            sku_weight = 0.0
            for rs in product_info.get("raw_data", {}).get("variation", {}).get("skus", {}).get("data", []):
                if str(rs.get("id")) == str(sku.get("id")):
                    try:
                        freight_dict = rs.get("freight") or {}
                        sku_weight = float(freight_dict.get("single_sku_weight", 0.0) or 0.0)
                    except Exception:
                        pass
                    break

            # Guard against dummy/fake supplier weights (e.g. 0.001 kg / 1g)
            # Real cases weigh 30-50g; minimum realistic air shipping is 50-80 BDT (default floor 50.0 BDT)
            if sku_weight >= 0.02:
                sku_air_ship = max(50.0, round(sku_weight * 2.0 * 780.0, 2))
            elif air_ship is not None and air_ship > 0:
                sku_air_ship = max(50.0, air_ship)
            else:
                sku_air_ship = 50.0

            landing = calculate_landing_cost(prod_price, china_del, sku_air_ship, bd_del, packaging, printing, other)
            margin_val = calculate_margin(landing)
            sell_p = calculate_sell_price(margin_val)
            max_d = calculate_max_discount(sell_p)

            local_path = f"{model_name}/{material}/sku/{sku_code}.jpg"

            row = {
                "Product Code": sku_code,
                "SEO Title": generate_seo_title(title, model_name, material),
                "Product Name": title,
                "Material": material,
                "Color": color_name,
                "Phone Model": model_name,
                "Warranty": "No",
                "source link": "Link",
                "link": product_url,
                "Local Image Path": local_path,
                "product price": prod_price,
                "china delivery": china_del,
                "air shipping": sku_air_ship,
                "bd delivery": bd_del,
                "packaging": packaging,
                "printing": printing,
                "other": other,
                "landing cost": landing,
                "margin": margin_val,
                "sell price": sell_p,
                "max discount": max_d
            }

            # If row already exists in existing_rows for this product link and SKU, update in-place
            updated_existing = False
            for r in existing_rows:
                if r.get("link") == product_url and r.get("Product Code") == sku_code:
                    r["SEO Title"] = row["SEO Title"]
                    r["Product Name"] = row["Product Name"]
                    r["Material"] = row["Material"]
                    r["Color"] = row["Color"]
                    r["Phone Model"] = row["Phone Model"]
                    r["product price"] = prod_price
                    r["china delivery"] = china_del
                    r["air shipping"] = sku_air_ship
                    r["bd delivery"] = bd_del
                    r["packaging"] = packaging
                    r["printing"] = printing
                    r["other"] = other
                    r["landing cost"] = landing
                    r["margin"] = margin_val
                    r["sell price"] = sell_p
                    r["max discount"] = max_d
                    r["Local Image Path"] = local_path
                    updated_existing = True
                    updated_count += 1
                    break

            if not updated_existing:
                new_rows.append(row)

    all_rows = existing_rows + new_rows
    save_to_csv(all_rows)
    save_to_excel(all_rows)
    if new_rows:
        print(f"[+] Appended {len(new_rows)} new SKU records to inventory.csv and inventory.xlsx")
    if updated_count:
        print(f"[+] Updated {updated_count} existing SKU records in inventory.csv and inventory.xlsx")

def sync_csv_to_excel(csv_path: str = INVENTORY_CSV_PATH, xlsx_path: str = INVENTORY_XLSX_PATH) -> int:
    """Reads inventory.csv and regenerates inventory.xlsx with styled headers and dynamic formulas."""
    if not os.path.exists(csv_path):
        print(f"[!] CSV file not found: {csv_path}")
        return 0
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    # Ensure SEO Title is populated on all rows
    updated_csv = False
    for r in rows:
        if not r.get("SEO Title"):
            r["SEO Title"] = generate_seo_title(r.get("Product Name", ""), r.get("Phone Model", ""), r.get("Material", ""))
            updated_csv = True

    # Ensure inventory.csv has UTF-8 BOM
    has_bom = False
    try:
        with open(csv_path, "rb") as bf:
            has_bom = bf.read(3) == b'\xef\xbb\xbf'
    except Exception:
        pass

    if updated_csv or not has_bom:
        save_to_csv(rows, csv_path)

    save_to_excel(rows, xlsx_path)
    print(f"[✓] Successfully synced {len(rows)} records from {os.path.basename(csv_path)} to {os.path.basename(xlsx_path)}")
    return len(rows)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CoverStore Inventory Manager & Synchronizer")
    parser.add_argument("--update-excel", "-u", action="store_true", help="Synchronize inventory.xlsx directly from inventory.csv")
    parser.add_argument("--sync-live", "-s", action="store_true", help="Perform full live Google Sheet synchronization")
    parser.add_argument("--china-delivery", "-c", type=float, default=None, help="China domestic delivery fee in BDT per unit")
    args = parser.parse_args()

    if args.update_excel:
        sync_csv_to_excel()
    elif args.sync_live:
        sync_inventory()
    else:
        # Default behavior: ensure Excel is up to date with CSV
        sync_csv_to_excel()
