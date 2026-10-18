# CoverStore - Project Guidelines & Automation Rules

## 1. Automatic Git Push
- **After completing work on each prompt or user request**, always:
  1. Stage all new or modified files (`git add .`).
  2. Create a clean, descriptive commit (`git commit -m "..."`).
  3. Push immediately to the remote repository (`git push origin main`).

## 2. Strict Single-Product Scope
- Only process the exact MoveOn URL provided by the user.
- Never crawl, pre-fetch, or spider any unprovided, recommended, or related links.

## 3. Storage Hierarchy (2-Folder Structure)
- Plan PDF: `plan/plan.pdf`
- Python Scripts: `scripts/`
- Downloaded Assets: `[phone model]/[material]/`
  - `gallery/`: Product showcase & gallery images (`gallery_01.jpg`, `gallery_02.jpg`, ...). Any non-English text is translated in-place directly replacing the original picture.
  - `sku/`: Color/variant cover images named with the custom SKU format (`[SKU].jpg`, e.g., `RN8-SIL-WT-S.jpg`). Any non-English text is translated in-place directly replacing the original picture.

## 4. Custom SKU Generation Standard
- Format: `[model abbreviation]-[material abbreviation]-[color abbreviation]-[print abbreviation]`
- Example: `RN8-SIL-WT-S`
- Components:
  - **Phone Model**: e.g., `RN8` (Realme Neo8), `IP15PM` (iPhone 15 Pro Max), `S24U` (Galaxy S24 Ultra).
  - **Material**: e.g., `SIL` (Liquid Silicone / Silicone), `GLS` (Glass), `TPU` (TPU), `LTH` (Leather), `PC` (Hard PC).
  - **Color**: e.g., `WT` (Antique White), `BK` (Classic Black), `PR` (Grass Purple), `GN` (Dark Night Green), `BL` (Royal Blue), `GY` (Lavender Gray), `RD` (Camellia Red), `TL` (Light Teal), `CL` (Transparent/Clear).
  - **Print / Finish**: e.g., `S` (Solid / Cube / Plain), `P` (Printed / Pattern / Graphic), `G` (Gradient), `E` (Electroplated / Mirror), `C` (Clear).

## 5. Inventory Dataset Standard (Google Sheets Sync)
- **Synchronization Files**: `inventory.csv` (UTF-8 with BOM) and `inventory.xlsx` (formatted with styled headers and auto-column widths).
- **Sync Script**: `scripts/inventory_manager.py` fetches the live Google Sheet, enriches existing rows with live MoveOn pricing, stock, weight, and image URLs, and appends newly downloaded products.
- **13-Column Schema**:
  1. `Product Name`: Full product title.
  2. `Product Code`: Custom SKU (`[model]-[material]-[color]-[finish]`).
  3. `Material`: Identified material (e.g., Liquid Silicone).
  4. `Color`: Variant color name.
  5. `Phone Model`: Exact phone model name (e.g., Realme Neo8).
  6. `Warranty`: Warranty status (`No` / `Yes`).
  7. `source link`: MoveOn base URL or source label.
  8. `link`: Exact product link.
  9. `Price (CNY)`: Dropship/wholesale price in CNY.
  10. `Stock`: Available inventory stock count.
  11. `Weight (kg)`: Single SKU freight weight in kg.
  12. `Image URL`: Remote CDN image link.
  13. `Local Image Path`: Relative local filepath to the variant image (e.g., `Realme Neo8/Liquid Silicone/sku/RN8-SIL-WT-S.jpg`).
- **Automatic Sync**: Whenever `scripts/downloader.py` finishes downloading and translating assets, it automatically invokes `append_downloaded_product` to append newly processed variants to `inventory.csv` and `inventory.xlsx`.
