# E2E Test Infra: CoverStore 3-Agent Catalog Automation Pipeline

## Test Philosophy
- **Requirement-Driven & Opaque-Box**: Derived strictly from `ORIGINAL_REQUEST.md` and `GEMINI.md`, testing the pipeline through its public CLI and standard file inputs/outputs.
- **Methodology**: Systematic 4-tier approach (Category-Partition, Boundary Value Analysis, Pairwise Combinatorial, and Real-World Workload Testing).
- **Progressive Testability**: Early tests require only file existence and schema conformance; later tiers verify full end-to-end integration and storefront data structures.

## Feature Inventory & Test Mapping
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 |
|---|---------|--------|:------:|:------:|:------:|
| 1 | MoveOn URL Parsing & Composite ID | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ |
| 2 | MoveOn Auth & Wholesale Fallback | GEMINI Rule 8 | 5 | 5 | ✓ |
| 3 | Gallery Ingestion & URL Parsing Fix | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ |
| 4 | 2-Folder Storage Directory Hierarchy | GEMINI Rule 3 | 5 | 5 | ✓ |
| 5 | Custom SKU Generation Standard | GEMINI Rule 4 | 5 | 5 | ✓ |
| 6 | SKU Collision & Grill-Me Handling | GEMINI Rule 7 | 5 | 5 | ✓ |
| 7 | Shared Variant Image Caching | ORIGINAL_REQUEST R1 | 5 | 5 | ✓ |
| 8 | Mandatory China Delivery Charge | GEMINI Rule 9 | 5 | 5 | ✓ |
| 9 | Financial Pricing & 21-Column Schema | GEMINI Rule 5 | 5 | 5 | ✓ |
| 10 | Standalone Image Translator CLI | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ |
| 11 | Normalized Relative Layouts | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ |
| 12 | Inpainting & Gradient Restoration | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ |
| 13 | Dynamic Typography Autoscaling | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ |
| 14 | Dual-Tier Translation Engine | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ |
| 15 | Watermark Removal | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ |
| 16 | Lossless In-Place Overwriting | ORIGINAL_REQUEST R2 | 5 | 5 | ✓ |
| 17 | Pathao Session Authentication | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ |
| 18 | Category ID 752 Hierarchy | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ |
| 19 | Markdown Marketing Copy Generation | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ |
| 20 | CDN Media Asset Reconciliation | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ |
| 21 | 16-Column Import Generation | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ |
| 22 | Bulk Import Automation & Conflict Check | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ |
| 23 | Pathao Dry-Run Mode & API Check | ORIGINAL_REQUEST R3 | 5 | 5 | ✓ |
| 24 | Unified Pipeline Orchestrator CLI | ORIGINAL_REQUEST R4 | 5 | 5 | ✓ |
| 25 | Git Stage, Commit & Push Standard | GEMINI Rule 1 | 5 | 5 | ✓ |
| 26 | Multi-PC 20-Minute Auto-Sync | GEMINI Rule 6 | 5 | 5 | ✓ |

## Test Architecture
- **Test Runner**: `python -m unittest discover -s tests/e2e -p "test_*.py"` or dedicated runner `python tests/e2e/runner.py`.
- **Pass/Fail Semantics**: All test suites must return exit code 0.
- **Directory Layout**:
  - `tests/e2e/test_tier1_features.py`: Isolated feature verification (T1).
  - `tests/e2e/test_tier2_boundaries.py`: Edge cases, invalid inputs, empty sets, limits (T2).
  - `tests/e2e/test_tier3_pairwise.py`: Cross-feature interactions and data handoffs (T3).
  - `tests/e2e/test_tier4_workloads.py`: Full end-to-end multi-agent pipeline executions (T4).

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Lifecycle: Realme Neo8 Liquid Silicone Ingestion -> Translation -> Pathao Workbook | F1, F3, F4, F5, F8, F9, F10, F12, F13, F14, F16, F17, F18, F19, F21, F23, F24 | High |
| 2 | High-Resolution Frosted PC Case (1600x1600) with Complex Layout & Multiple Colors | F4, F5, F10, F11, F12, F13, F14, F16, F21 | High |
| 3 | Duplicate SKU Collision Simulation with Disambiguation Propagation | F5, F6, F7, F9, F16, F21 | High |
| 4 | Offline Translation Fallback & Zero-Auth Resiliency | F10, F14, F16, F24 | Medium |
| 5 | Pathao Commerce Dry-Run Sync for Multi-Model Catalog | F17, F18, F19, F20, F21, F22, F23 | High |
| 6 | 20-Minute Git Auto-Sync Rebase & Locked Excel Conflict Resolution | F25, F26 | Medium |

## Coverage Thresholds
- Tier 1: ≥ 130 tests (5 per feature across 26 features)
- Tier 2: ≥ 130 tests (boundary & corner cases)
- Tier 3: ≥ 26 cross-feature interaction tests
- Tier 4: ≥ 6 realistic application-level scenarios
- Total: ≥ 292 test assertions across the E2E test suite
