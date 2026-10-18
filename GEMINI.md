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

## 5. Inventory Dataset Standard (Financial & Pricing Schema)
- **Synchronization Files**: `inventory.csv` (UTF-8 with BOM) and `inventory.xlsx` (styled headers, auto-column widths, and live Excel formulas).
- **Sync Script**: `scripts/inventory_manager.py` merges Google Sheet metadata, preserves historical unit logistics costs, and computes financial formulas.
- **20-Column Schema**:
  1. `Product Name`: Full product title.
  2. `Product Code`: Custom SKU (`[model]-[material]-[color]-[finish]`).
  3. `Material`: Identified material (e.g., Liquid Silicone).
  4. `Color`: Variant color name.
  5. `Phone Model`: Exact phone model name (e.g., Realme Neo8).
  6. `Warranty`: Warranty status (`No` / `Yes`).
  7. `source link`: MoveOn base URL or source label.
  8. `link`: Exact product link.
  9. `Local Image Path`: Relative local filepath to the variant image (e.g., `Realme Neo8/Liquid Silicone/sku/RN8-SIL-WT-S.jpg`).
  10. `product price`: Base unit procurement price in BDT (collected from MoveOn dropship price * 1.1703).
  11. `china delivery`: China domestic logistics share per unit (manual input by user, default 10.0 BDT).
  12. `air shipping`: International air freight share per unit (`weight x 2 x 780/kg`, default 50.0 BDT).
  13. `bd delivery`: Bangladesh local delivery share per unit (fixed 5.0 BDT).
  14. `packaging`: Packaging material cost (fixed 11.5 Taka).
  15. `printing`: Labeling/printing cost (fixed 20.0 Taka).
  16. `other`: Miscellaneous expenses (default 0.0 BDT).
  17. `landing cost`: Total unit cost: `=SUM(J{r}:P{r})`.
  18. `margin`: Dynamic markup: `=IF(Q{r}<300, Q{r}*1.4, IF(Q{r}<400, Q{r}*1.33, Q{r}*1.25))`.
  19. `sell price`: Rounding ending in `00` (<25), `49` (25–74), or `99` (75–99): `=INT(R{r}/100)*100 + IF(MOD(ROUND(R{r},0),100)<25, 0, IF(MOD(ROUND(R{r},0),100)<=74, 49, 99))`.
  20. `max discount`: Tiered ceiling discount formula: `=IF(S{r}<300, 0, MIN(99, IF(S{r}<500, S{r}*7%, IF(S{r}<700, S{r}*12%, S{r}*15%))))`.
- **Automatic Sync**: Whenever `scripts/downloader.py` finishes downloading and translating assets, it automatically invokes `append_downloaded_product` to append newly processed variants with default financial figures to `inventory.csv` and `inventory.xlsx`.

## 6. Multi-PC 20-Minute Auto-Sync Standard
- **Multi-PC Operation**: The repository is actively operated across 2 separate workstations.
- **Sync Cadence**: Synchronizes every 20 minutes aligned to standard clock boundaries (`:00`, `:20`, `:40` past the hour).
- **Sync Engine**: `scripts/auto_sync.py` and `scripts/run_auto_sync.bat`.
  - Automatically pulls remote changes with `--rebase --autostash` to integrate the other workstation's work safely.
  - Automatically regenerates and synchronizes `inventory.xlsx` from `inventory.csv` to prevent binary merge conflicts and preserve live pricing formulas.
  - Stages all new and modified local assets and files (`git add .`).
  - Creates a descriptive commit (`chore: auto-sync [hostname] [timestamp]`).
  - Pushes directly to `origin main` to keep both PCs in continuous sync.

