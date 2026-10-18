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
