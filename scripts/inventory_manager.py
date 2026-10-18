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

from moveon_client import MoveOnClient, extract_product_id_from_url
from sku_generator import generate_sku

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INVENTORY_CSV_PATH = os.path.join(WORKSPACE_ROOT, "inventory.csv")
INVENTORY_XLSX_PATH = os.path.join(WORKSPACE_ROOT, "inventory.xlsx")
GOOGLE_SHEET_XLSX_URL = "https://docs.google.com/spreadsheets/d/1cfLya8zgGBLZfor3g7-ljrjw7lmo3J28uxkqiOONzhk/export?format=xlsx"

# 20-Column Financial Schema
FIELDNAMES = [
    "Product Code",       # A (1)
    "Product Name",       # B (2)
    "Material",           # C (3)
    "Color",              # D (4)
    "Phone Model",        # E (5)
    "Warranty",           # F (6)
    "source link",        # G (7)
    "link",               # H (8)
    "Local Image Path",   # I (9)
    "product price",      # J (10)
    "china delivery",     # K (11)
    "air shipping",       # L (12)
    "bd delivery",        # M (13)
    "packaging",          # N (14)
    "printing",           # O (15)
    "other",              # P (16)
    "landing cost",       # Q (17)
    "margin",             # R (18)
    "sell price",         # S (19)
    "max discount"        # T (20)
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
                row_vals.append(f"=SUM(J{row_idx}:P{row_idx})")
            elif k == "margin":
                row_vals.append(f"=IF(Q{row_idx}<300, Q{row_idx}*1.4, IF(Q{row_idx}<400, Q{row_idx}*1.33, Q{row_idx}*1.25))")
            elif k == "sell price":
                row_vals.append(f"=INT(R{row_idx}/100)*100 + IF(MOD(ROUND(R{row_idx},0),100)<25, 0, IF(MOD(ROUND(R{row_idx},0),100)<=74, 49, 99))")
            elif k == "max discount":
                row_vals.append(f"=IF(S{row_idx}<300, 0, MIN(99, IF(S{row_idx}<500, S{row_idx}*7%, IF(S{row_idx}<700, S{row_idx}*12%, S{row_idx}*15%))))")
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
            
            # Wholesale BDT price (MoveOn dropship price * 1.1703)
            prod_price = round(float(price_val) * 1.1703, 2)
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
                "Product Name": title,
                "Product Code": sku_code,
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
    china_del: float = 10.0,
    air_ship: Optional[float] = None,
    bd_del: float = 5.0,
    packaging: float = 11.5,
    printing: float = 20.0,
    other: float = 0.0
):
    """
    Appends newly downloaded product variants into inventory.csv and inventory.xlsx using 20-column schema.
    """
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
    for model_meta in selected_models:
        model_name = model_meta["clean_name"]
        model_skus = skus_by_model.get(model_name, [])
        if not model_skus and len(selected_models) == 1:
            for v in skus_by_model.values():
                model_skus.extend(v)

        for sku in model_skus:
            variant_label = sku.get("variant_label", "")
            sku_code = generate_sku(model_name, material, variant_label, title)
            if sku_code in existing_codes:
                continue
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
            prod_price = round(float(price_val) * 1.1703, 2)
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

            if sku_weight > 0:
                sku_air_ship = round(sku_weight * 2.0 * 780.0, 2)
            elif air_ship is not None and air_ship > 0:
                sku_air_ship = air_ship
            else:
                sku_air_ship = 50.0

            landing = calculate_landing_cost(prod_price, china_del, sku_air_ship, bd_del, packaging, printing, other)
            margin_val = calculate_margin(landing)
            sell_p = calculate_sell_price(margin_val)
            max_d = calculate_max_discount(sell_p)

            local_path = f"{model_name}/{material}/sku/{sku_code}.jpg"

            row = {
                "Product Name": title,
                "Product Code": sku_code,
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
            new_rows.append(row)

    if new_rows:
        all_rows = existing_rows + new_rows
        save_to_csv(all_rows)
        save_to_excel(all_rows)
        print(f"[+] Appended {len(new_rows)} new SKU records to inventory.csv and inventory.xlsx")
    else:
        # Ensure inventory.xlsx has all records matching CSV
        save_to_excel(existing_rows)
        print(f"[+] All {len(existing_codes)} SKU records are already up to date in inventory.csv and inventory.xlsx")

def sync_csv_to_excel(csv_path: str = INVENTORY_CSV_PATH, xlsx_path: str = INVENTORY_XLSX_PATH) -> int:
    """Reads inventory.csv and regenerates inventory.xlsx with styled headers and dynamic formulas."""
    if not os.path.exists(csv_path):
        print(f"[!] CSV file not found: {csv_path}")
        return 0
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    save_to_excel(rows, xlsx_path)
    print(f"[✓] Successfully synced {len(rows)} records from {os.path.basename(csv_path)} to {os.path.basename(xlsx_path)}")
    return len(rows)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CoverStore Inventory Manager & Synchronizer")
    parser.add_argument("--update-excel", "-u", action="store_true", help="Synchronize inventory.xlsx directly from inventory.csv")
    parser.add_argument("--sync-live", "-s", action="store_true", help="Perform full live Google Sheet synchronization")
    args = parser.parse_args()

    if args.update_excel:
        sync_csv_to_excel()
    elif args.sync_live:
        sync_inventory()
    else:
        # Default behavior: ensure Excel is up to date with CSV
        sync_csv_to_excel()
