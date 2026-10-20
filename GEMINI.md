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
- **21-Column Schema**:
  1. `Product Code`: Custom SKU (`[model]-[material]-[color]-[finish]`).
  2. `SEO Title`: Premium, SEO-optimized title for Daraz listing.
  3. `Product Name`: Full product title / supplier title.
  4. `Material`: Identified material (e.g., Liquid Silicone).
  5. `Color`: Variant color name.
  6. `Phone Model`: Exact phone model name (e.g., Realme Neo8).
  7. `Warranty`: Warranty status (`No` / `Yes`).
  8. `source link`: MoveOn base URL or source label.
  9. `link`: Exact product link.
  10. `Local Image Path`: Relative local filepath to the variant image (e.g., `Realme Neo8/Liquid Silicone/sku/RN8-SIL-WT-S.jpg`).
  11. `product price`: Base unit procurement price in BDT (collected directly from MoveOn dropship/offer price, which is natively in BDT; do NOT multiply by 1.1703).
  12. `china delivery`: China domestic logistics share per unit (manual input by user, default 10.0 BDT).
  13. `air shipping`: International air freight share per unit (`weight x 2 x 780/kg`, default floor 50.0 BDT; dummy/fake weights < 0.02kg fallback to 50.0–80.0 BDT baseline).
  14. `bd delivery`: Bangladesh local delivery share per unit (fixed 5.0 BDT).
  15. `packaging`: Packaging material cost (fixed 11.5 Taka).
  16. `printing`: Labeling/printing cost (fixed 20.0 Taka).
  17. `other`: Miscellaneous expenses (default 0.0 BDT).
  18. `landing cost`: Total unit cost: `=SUM(K{r}:Q{r})`.
  19. `margin`: Dynamic markup: `=IF(R{r}<300, R{r}*1.4, IF(R{r}<400, R{r}*1.33, R{r}*1.25))`.
  20. `sell price`: Rounding ending in `00` (<25), `49` (25–74), or `99` (75–99): `=INT(S{r}/100)*100 + IF(MOD(ROUND(S{r},0),100)<25, 0, IF(MOD(ROUND(S{r},0),100)<=74, 49, 99))`.
  21. `max discount`: Tiered ceiling discount formula: `=IF(T{r}<300, 0, MIN(99, IF(T{r}<500, T{r}*7%, IF(T{r}<700, T{r}*12%, T{r}*15%))))`.
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



## 7. Duplicate SKU Collision & /grill-me Standard
- **Scope**: Enforced on all future product imports from MoveOn links (legacy inventory records remain untouched).
- **Trigger Condition**: When two distinct variants generate identical SKU codes, or a newly processed variant's SKU collides with an existing SKU code.
- **Interactive Resolution**:
  - Automatically pause and initiate a `/grill-me` interview with the user.
  - Auto-generate candidate disambiguated codes with a unique suffix (e.g. `-V2`, `-V3`) or custom color/finish abbreviation.
  - Prompt the user to confirm or edit the suggested unique SKU.
- **Propagation**:
  - Apply the confirmed unique SKU to the variant image filename in `sku/` (`[SKU]-V2.jpg`).
  - Save the unique SKU in `inventory.csv` and `inventory.xlsx`.
  - Update `COLOR_MAP` or abbreviation rules in `scripts/sku_generator.py` to persist the resolution standard and prevent recurrent collisions.


## 8. MoveOn Business Account Crawling Standard
- **Scope**: All MoveOn product downloads and pricing synchronization.
- **Authentication**: Supports authenticated MoveOn Business Account requests using:
  1. Automated Email & Password login (MOVEON_EMAIL and MOVEON_PASSWORD in .env) with Playwright browser session caching (.moveon_session.json).
  2. Direct Bearer token stored in .env as MOVEON_AUTH_TOKEN (or via --token).
- **Wholesale Tier Pricing**:
  - Automatically queries MoveOn's wholesale endpoints with `business_type=wholesale`.
  - Attaches `Authorization: Bearer <token>` when available.
  - Automatically extracts business pricing and volume tier discounts (`wholesales` and `dropship.offer_price`).
  - Gracefully falls back to guest wholesale mode if no token is configured in `.env`.
- **Security & Multi-PC Safety**:
  - `.env` is permanently excluded via `.gitignore` to prevent leaking private business account tokens.
  - An `.env.example` template is provided for quick setup across both workstations.


## 9. Mandatory China Domestic Delivery Charge /grill-me Standard
- **Scope**: Every single product processed from a MoveOn link.
- **Timing**: Triggered immediately after asset download and in-place translation finish, right before calculating financial landing costs and appending to `inventory.csv` & `inventory.xlsx`.
- **Mandatory Prompt**:
  - Never assume, hardcode, or silently default China domestic delivery charge.
  - Automatically pause and grill the user via `ask_question` to input the exact China domestic delivery fee in BDT per unit for the current product shipment.
- **Propagation**:
  - Apply the user's exact specified fee to the `china delivery` column (Column 12 / L).
  - Compute `landing cost`, `margin`, `sell price`, and `max discount` using this confirmed logistics cost.
