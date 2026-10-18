import os
import sys
import csv
import io
import urllib.request
import urllib.error
import json
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

INVENTORY_CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "inventory.csv"))
INVENTORY_XLSX_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "inventory.xlsx"))
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1cfLya8zgGBLZfor3g7-ljrjw7lmo3J28uxkqiOONzhk/export?format=csv&gid=641365888"

FIELDNAMES = [
    "Product Name",
    "Product Code",
    "Material",
    "Color",
    "Phone Model",
    "Warranty",
    "source link",
    "link",
    "Price (CNY)",
    "Stock",
    "Weight (kg)",
    "Image URL",
    "Local Image Path"
]

def fetch_live_google_sheet_rows() -> List[Dict[str, str]]:
    """Fetches the current rows from the live Google Sheet."""
    req = urllib.request.Request(GOOGLE_SHEET_CSV_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            reader = csv.reader(io.StringIO(content))
            raw_rows = list(reader)
            if not raw_rows:
                return []
            
            headers = [h.strip() for h in raw_rows[0]]
            rows = []
            for r in raw_rows[1:]:
                if not any(r):
                    continue
                row_dict = {}
                for idx, col_name in enumerate(headers):
                    val = r[idx] if idx < len(r) else ""
                    row_dict[col_name] = val
                rows.append(row_dict)
            return rows
    except Exception as e:
        print(f"[!] Warning: Could not fetch live Google Sheet: {e}")
        return []

def enrich_existing_row(row: Dict[str, str], moveon_cache: Dict[str, Any]) -> Dict[str, str]:
    """Enriches an existing row with info-based fields (Price, Stock, Weight, Image URL) from MoveOn API."""
    link = row.get("link", "").strip()
    if not link:
        return row

    client = MoveOnClient()
    prod_data = None
    if link in moveon_cache:
        prod_data = moveon_cache[link]
    else:
        try:
            prod_data = client.fetch_product(link)
            moveon_cache[link] = prod_data
        except Exception:
            moveon_cache[link] = None

    if prod_data:
        # Find matching SKU if possible
        color_query = row.get("Color", "").lower()
        model_query = row.get("Phone Model", "").lower()
        skus_by_model = prod_data.get("skus_by_model", {})
        
        matched_sku = None
        for m_name, sku_list in skus_by_model.items():
            if model_query in m_name.lower() or m_name.lower() in model_query:
                for sku in sku_list:
                    lbl = sku.get("variant_label", "").lower()
                    if any(c in lbl for c in color_query.split()) or not color_query:
                        matched_sku = sku
                        break
            if matched_sku:
                break
        
        if not matched_sku and skus_by_model:
            # Take first SKU of matching model or first overall
            first_key = list(skus_by_model.keys())[0]
            if skus_by_model[first_key]:
                matched_sku = skus_by_model[first_key][0]

        if matched_sku:
            price_dict = matched_sku.get("price", {})
            dropship = price_dict.get("dropship", {})
            price_val = dropship.get("offer_price") or price_dict.get("original") or ""
            row["Price (CNY)"] = str(round(float(price_val), 2)) if price_val else ""
            
            raw_skus = prod_data.get("raw_data", {}).get("variation", {}).get("skus", {}).get("data", [])
            for rs in raw_skus:
                if str(rs.get("id")) == str(matched_sku.get("id")):
                    row["Stock"] = str(rs.get("stock", {}).get("available", ""))
                    row["Weight (kg)"] = str(rs.get("freight", {}).get("single_sku_weight", ""))
                    break
            
            row["Image URL"] = matched_sku.get("image") or prod_data.get("main_image") or ""
        else:
            row["Image URL"] = prod_data.get("main_image") or ""

    return row

def save_to_csv(rows: List[Dict[str, str]], filepath: str = INVENTORY_CSV_PATH):
    """Saves inventory rows to CSV with UTF-8 encoding."""
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            # Ensure all keys exist
            clean_row = {k: r.get(k, "") for k in FIELDNAMES}
            writer.writerow(clean_row)
    print(f"[+] Successfully saved {len(rows)} records to CSV: {filepath}")

def save_to_excel(rows: List[Dict[str, str]], filepath: str = INVENTORY_XLSX_PATH):
    """Saves inventory rows to beautifully formatted Excel file with freeze panes and styled headers."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    # Style definitions
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    data_font = Font(name="Calibri", size=10)
    alt_fill = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
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
        row_vals = [r.get(k, "") for k in FIELDNAMES]
        ws.append(row_vals)
        use_alt = (row_idx % 2 == 0)
        for col_idx in range(1, len(FIELDNAMES) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = thin_border
            if use_alt:
                cell.fill = alt_fill
            # Align numeric columns center
            if FIELDNAMES[col_idx - 1] in ["Product Code", "Material", "Color", "Phone Model", "Warranty", "Price (CNY)", "Stock", "Weight (kg)"]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

    # Freeze header row
    ws.freeze_panes = "A2"

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    try:
        wb.save(filepath)
        print(f"[+] Successfully saved {len(rows)} records to Excel: {filepath}")
    except PermissionError:
        alt_path = os.path.splitext(filepath)[0] + "_updated.xlsx"
        try:
            wb.save(alt_path)
            print(f"[!] Notice: '{os.path.basename(filepath)}' is currently open in Excel. Saved updated copy to '{os.path.basename(alt_path)}'.")
        except Exception as e:
            print(f"[!] Warning: Could not save Excel file: {e}")

def sync_inventory():
    """Performs full sync: live sheet + MoveOn enrichment + Realme Neo8 append."""
    print("[*] Fetching live Google Sheet rows...")
    raw_sheet_rows = fetch_live_google_sheet_rows()
    print(f"    Found {len(raw_sheet_rows)} rows in live Google Sheet.")

    moveon_cache = {}
    enriched_rows = []
    print("[*] Enriching existing rows with MoveOn product data...")
    for idx, r in enumerate(raw_sheet_rows, 1):
        enriched = enrich_existing_row(r, moveon_cache)
        enriched_rows.append(enriched)

    # Fetch Realme Neo8 product data to append
    rn8_url = "https://moveon.global/BD_en/products/0000000MJPDSKGCI-suitable-for-realme-neo8-phone-case-simple-solid-color-cube-liquid-silicone-full-cover-anti-drop-soft-case-new-model/1AD8354574484115"
    client = MoveOnClient()
    try:
        rn8_data = client.fetch_product(rn8_url)
        title = rn8_data["title"]
        material = "Liquid Silicone"
        model_name = "Realme Neo8"
        skus_data = rn8_data.get("raw_data", {}).get("variation", {}).get("skus", {}).get("data", [])
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
            price_val = dropship.get("offer_price") or price_dict.get("original") or ""
            price_str = str(round(float(price_val), 2)) if price_val else "31.14"

            stock_str = ""
            weight_str = ""
            for rs in skus_data:
                if str(rs.get("id")) == str(sku.get("id")):
                    stock_str = str(rs.get("stock", {}).get("available", "999219"))
                    weight_str = str(rs.get("freight", {}).get("single_sku_weight", "0.03"))
                    break

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
                "Price (CNY)": price_str,
                "Stock": stock_str or "999219",
                "Weight (kg)": weight_str or "0.03",
                "Image URL": sku.get("image", ""),
                "Local Image Path": local_path
            }
            enriched_rows.append(new_row)
    except Exception as e:
        print(f"[!] Error appending Realme Neo8 data: {e}")

    # Save to CSV and XLSX
    save_to_csv(enriched_rows)
    save_to_excel(enriched_rows)
    print(f"\n[✓] Inventory synchronization complete! Total rows: {len(enriched_rows)}")

def append_downloaded_product(product_info: Dict[str, Any], selected_models: List[Dict[str, str]], material: str, product_url: str):
    """
    Appends newly downloaded product variants into inventory.csv and inventory.xlsx.
    """
    title = product_info.get("title", "")
    skus_data = product_info.get("raw_data", {}).get("variation", {}).get("skus", {}).get("data", [])
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
            for prefix in ["Straight Edge New Model [", "Rubik's Cube Liquid Silicone", "]"]:
                color_name = color_name.replace(prefix, "")
            color_name = color_name.strip()

            price_dict = sku.get("price", {})
            dropship = price_dict.get("dropship", {})
            price_val = dropship.get("offer_price") or price_dict.get("original") or ""
            price_str = str(round(float(price_val), 2)) if price_val else ""

            stock_str = ""
            weight_str = ""
            for rs in skus_data:
                if str(rs.get("id")) == str(sku.get("id")):
                    stock_str = str(rs.get("stock", {}).get("available", ""))
                    weight_str = str(rs.get("freight", {}).get("single_sku_weight", ""))
                    break

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
                "Price (CNY)": price_str,
                "Stock": stock_str,
                "Weight (kg)": weight_str,
                "Image URL": sku.get("image", ""),
                "Local Image Path": local_path
            }
            new_rows.append(row)

    if new_rows:
        all_rows = existing_rows + new_rows
        save_to_csv(all_rows)
        save_to_excel(all_rows)
        print(f"[+] Appended {len(new_rows)} new SKU records to inventory.csv and inventory.xlsx")

if __name__ == "__main__":
    sync_inventory()
