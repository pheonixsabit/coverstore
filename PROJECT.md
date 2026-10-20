# Project: CoverStore 3-Agent Catalog Automation Pipeline

## Architecture
The system is an automated, modular e-commerce catalog ingestion, visual localization, and marketplace publication pipeline consisting of three core autonomous agents coordinated by a unified pipeline orchestrator:
```
[MoveOn Single Product URL]
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent 1: MoveOn Ingestion & Pricing Agent                   │
│ (scripts/downloader.py & scripts/moveon_client.py)          │
│ - Authenticates / queries MoveOn wholesale endpoint         │
│ - Downloads gallery & variant images into 2-folder structure │
│ - Resolves custom SKUs, verifies collisions & grill-me      │
│ - Solicits China domestic delivery fee                      │
│ - Calculates financial formulas & writes inventory CSV/XLSX │
└─────────────────────────────────────────────────────────────┘
            │ Hand-off: Assets on disk + CSV/XLSX records
            ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent 2: In-Place Visual Image Translation Agent            │
│ (scripts/image_translator.py)                               │
│ - Discovers downloaded gallery and SKU images               │
│ - Classifies image layout (banners, spines, pills, watermarks)│
│ - Gradient inpainting / background color restoration        │
│ - Dynamic font autoscaling & high-quality English typography│
│ - Translates via Google API + offline 150+ term dictionary  │
│ - Overwrites original files in-place (same format & size)   │
└─────────────────────────────────────────────────────────────┘
            │ Hand-off: Local translated image paths
            ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent 3: Pathao Commerce Sync & Catalog Upload Agent        │
│ (scripts/pathao_sync.py)                                    │
│ - Authenticates via .pathao_session.json / headless browser │
│ - Matches inventory records by MoveOn link                  │
│ - Creates category 752 listing (Mobile Cases & Covers)      │
│ - Reconciles and uploads CDN gallery & variant SKU images   │
│ - Generates 16-column import workbook & executes import     │
│ - Verifies storefront creation & returns product ID         │
└─────────────────────────────────────────────────────────────┘
            │ Hand-off: Upload status & listing identifier
            ▼
┌─────────────────────────────────────────────────────────────┐
│ Unified Pipeline Orchestrator & Git Sync                    │
│ (scripts/pipeline_orchestrator.py)                          │
│ - End-to-end execution: Agent 1 -> Agent 2 -> Agent 3       │
│ - Enforces Git stage, descriptive commit, and push          │
│ - Verifies pipeline handoffs and maintains auto-sync safety │
└─────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | MoveOn URL Parsing & Querying | Parse composite product IDs and query wholesale API with guest fallback | M1 | ORIGINAL_REQUEST R1, Survey |
| 2 | MoveOn Business Authentication | Authenticate with MoveOn credentials/token via Playwright & session storage | M1 | GEMINI Rule 8 |
| 3 | Gallery Ingestion URL Fix | Fix `item.get('url')` parsing in `moveon_client.py:290` to capture all 5+ showcase images | M1 | Survey Bug 1 |
| 4 | 2-Folder Storage Hierarchy | Strictly store assets in `[phone model]/[material]/gallery/` and `.../sku/` | M1 | GEMINI Rule 3 |
| 5 | Custom SKU Generation Standard | Generate `[model]-[material]-[color]-[finish]` SKUs | M1 | GEMINI Rule 4 |
| 6 | SKU Collision & Grill-Me Resolution | Interactive `/grill-me` collision detection with disk & inventory synchronization | M1 | GEMINI Rule 7, Survey Bug 2 |
| 7 | Shared Variant Image Caching | Ensure each variant has dedicated `[SKU].jpg` on disk even when sharing supplier URLs | M1 | Survey Bug 3 |
| 8 | Mandatory China Delivery Charge | Solicit China domestic delivery fee per unit without silent default fallback | M1 | GEMINI Rule 9 |
| 9 | 21-Column Inventory Schema | Write UTF-8 BOM CSV and openpyxl XLSX with live Excel formulas | M1 | GEMINI Rule 5 |
| 10 | Standalone Image Translator Module | Implement `scripts/image_translator.py` with CLI and programmatic API | M2 | ORIGINAL_REQUEST R2, Survey |
| 11 | Normalized Relative Layouts | Dimension-agnostic relative coordinate $(W, H)$ bounding boxes | M2 | Survey |
| 12 | Seamless Background Restoration | Border pixel sampling, gradient inpainting, and clean color restoration | M2 | ORIGINAL_REQUEST R2, Survey |
| 13 | Typography Autoscaling | Dynamic font sizing (`fit_text`) preventing clipping and overflow | M2 | ORIGINAL_REQUEST R2, Survey |
| 14 | Multi-Tier Translation Engine | Real-time Google Translate API with 150+ term offline domain lexicon fallback | M2 | Survey |
| 15 | Watermark Removal | Clean supplier watermarks (e.g. `韩遇`) via local neighborhood pixel blending | M2 | Survey |
| 16 | Lossless In-Place Overwrite | Overwrite gallery & SKU images in-place preserving dimensions, format, and quality | M2 | ORIGINAL_REQUEST R2 |
| 17 | Pathao Session Authentication | Authenticate via `.pathao_session.json` Playwright storage state with auto-login fallback | M3 | ORIGINAL_REQUEST R3, Survey |
| 18 | Category Hierarchy Resolution | Canonical category ID `752` (`Mobile Cases & Covers`) | M3 | ORIGINAL_REQUEST R3, Survey |
| 19 | Rich Marketing Copy Generation | Dynamic product description based on material and model using `product description.md` | M3 | ORIGINAL_REQUEST R3, Survey |
| 20 | CDN Media Asset Upload | Query existing media and upload missing gallery and SKU images to Pathao CDN | M3 | ORIGINAL_REQUEST R3, Survey |
| 21 | 16-Column Import Workbook | Build openpyxl workbook mapping parent product on row 1 and variants on subsequent rows | M3 | ORIGINAL_REQUEST R3, Survey |
| 22 | 5-Step Bulk Import Automation | Drive warehouse selection, upload, mapping, analysis, and import submission with conflict check | M3 | ORIGINAL_REQUEST R3, Survey |
| 23 | Pathao Verification & Dry-Run | Dry-run mode (`--dry-run`) and post-upload verification via API | M3 | ORIGINAL_REQUEST R3, Survey |
| 24 | Unified Pipeline Orchestrator | CLI entrypoint `scripts/pipeline_orchestrator.py` chaining Agent 1 -> Agent 2 -> Agent 3 | M4 | ORIGINAL_REQUEST R4 |
| 25 | Automatic Git Push Standard | Automated `git add .`, descriptive commit, and `git push origin main` | M4 | GEMINI Rule 1 |
| 26 | Multi-PC 20-Min Auto-Sync | Clock-aligned sync integration with `--rebase --autostash` and lock protection | M4 | GEMINI Rule 6 |
| 27 | E2E Test Suite (Tiers 1-4) | Comprehensive opaque-box test runner covering all inventoried features | M5 | Project Pattern, Acceptance Criteria |
| 28 | Adversarial Coverage Hardening | Tier 5 adversarial stress testing on edge cases and error conditions | M5 | Project Pattern Tier 5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | MoveOn Ingestion & Pricing Agent (Agent 1) | Fix gallery parsing bug, SKU collision disk desync, shared URL caching, China delivery prompt, and inventory persistence | none | PLANNED |
| M2 | In-Place Visual Image Translation Agent (Agent 2) | Build `scripts/image_translator.py` with normalized bounding boxes, gradient inpainting, typography autoscaling, dual-tier translation, and in-place overwriting | none | PLANNED |
| M3 | Pathao Commerce Sync & Catalog Upload (Agent 3) | Enhance `scripts/pathao_sync.py` with robust session handling, dry-run, CDN upload, 16-column import, and verification | M1, M2 | PLANNED |
| M4 | Unified Pipeline Orchestrator & Git Sync (Agent 4) | Build `scripts/pipeline_orchestrator.py` chaining Agents 1 -> 2 -> 3 with git commit & push enforcement | M1, M2, M3 | PLANNED |
| M5 | Full E2E Test Suite & Adversarial Hardening | Pass 100% of E2E tests (Tiers 1-4) followed by Tier 5 adversarial coverage hardening | M1, M2, M3, M4 | PLANNED |

## Interface Contracts

### Agent 1 ↔ Agent 2 (Disk & Inventory Contract)
- **Input to Agent 1**: MoveOn Product URL (`str`), China domestic delivery charge (`float`), optional auth credentials.
- **Output from Agent 1**:
  - Image directory: `i:\coverstore\[phone model]\[material]\gallery\gallery_01.jpg...`
  - SKU directory: `i:\coverstore\[phone model]\[material]\sku\[SKU].jpg`
  - Records in `inventory.csv` (UTF-8 BOM) and `inventory.xlsx` (21 columns).
- **Handoff from Agent 1 to Agent 2**:
  - `model_name` (`str`, e.g., `"Realme Neo8"`).
  - `material` (`str`, e.g., `"Liquid Silicone"`).
  - `target_dir` (`str`, e.g., `"i:\\coverstore\\Realme Neo8\\Liquid Silicone"`).

### Agent 2 ↔ Agent 3 (Visual Assets Contract)
- **Input to Agent 2**: `target_dir`, `model_name`, `material`.
- **Output from Agent 2**: Overwritten image files at exact same paths (`gallery_*.jpg`, `[SKU].jpg`).
- **Invariance Guarantee**: Exact same image resolution, RGB color mode, and filename.
- **Handoff from Agent 2 to Agent 3**: MoveOn Product URL (`str`, matching `link` column in `inventory.csv`).

### Agent 3 ↔ Pipeline Orchestrator (Publication Contract)
- **Input to Agent 3**: `--link <MOVEON_URL>`, `--dry-run` flag, `--headless` flag.
- **Output from Agent 3**:
  - JSON execution report containing: `status` (`"success" | "error"`), `product_id` (`int`), `parent_sku` (`str`), `variants_count` (`int`), `live_url` (`str`).
  - Return exit code `0` on success, non-zero on failure.

### Unified Pipeline Orchestrator ↔ Git (Repository Contract)
- **Execution Command**:
  `python scripts/pipeline_orchestrator.py --url "<MOVEON_URL>" --china-delivery <BDT>`
- **Post-Execution Action**:
  - Stages modified/added files (`git add .`)
  - Commits with descriptive message (`feat: process <model> (<material>) - pipeline complete`)
  - Pushes directly to remote repository (`git push origin main`)

## Code Layout
- `i:\coverstore\scripts\`:
  - `moveon_client.py`: MoveOn API client and authentication (Owned by M1)
  - `downloader.py`: Ingestion coordinator and image downloader (Owned by M1)
  - `sku_generator.py`: Custom SKU generator and collision handler (Owned by M1)
  - `inventory_manager.py`: Financial formula engine and CSV/XLSX synchronizer (Owned by M1)
  - `image_translator.py`: In-place visual image translator (Owned by M2)
  - `translate_helper.py`: Domain lexicon and legacy translation helpers (Owned by M2)
  - `pathao_sync.py`: Pathao Commerce browser automation and catalog uploader (Owned by M3)
  - `pipeline_orchestrator.py`: Unified pipeline orchestrator (Owned by M4)
  - `auto_sync.py`: 20-minute clock-aligned Git auto-sync engine (Owned by M4)
- `i:\coverstore\tests\`:
  - `tests\e2e\`: Comprehensive 4-tier E2E opaque-box test runner and suites (Owned by E2E Testing Track)
