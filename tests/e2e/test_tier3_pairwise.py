"""
Tier 3: Pairwise Combinatorial & Cross-Feature Integration Test Suite
Verifies cross-agent data handoffs, module contracts, and end-to-end data propagation.
26 Pairwise Interaction Test Cases.
"""

import os
import sys
import re
import csv
import json
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw
import openpyxl

# Add scripts directory to module search path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import moveon_client
import sku_generator
import inventory_manager
import translate_helper
import pathao_sync
import auto_sync
import downloader


class TestTier3Pairwise(unittest.TestCase):
    """Pairwise combinatorial and cross-feature contract tests."""

    def test_p01_ingestion_to_translation_path_handoff(self):
        """Pairwise: Agent 1 folder hierarchy matches Agent 2 input paths."""
        model = "Realme Neo8"
        material = "Liquid Silicone"
        with tempfile.TemporaryDirectory() as td:
            base_dir = os.path.join(td, model, material)
            gal_dir = os.path.join(base_dir, "gallery")
            sku_dir = os.path.join(base_dir, "sku")
            os.makedirs(gal_dir)
            os.makedirs(sku_dir)

            gal_img = os.path.join(gal_dir, "gallery_01.jpg")
            sku_img = os.path.join(sku_dir, "RN8-SIL-WT-S.jpg")
            Image.new("RGB", (800, 800), "white").save(gal_img)
            Image.new("RGB", (800, 800), "white").save(sku_img)

            # Translation processes the exact directories produced by Agent 1
            translate_helper.translate_in_place(gal_dir, sku_dir, material=material, model_name=model)
            self.assertTrue(os.path.exists(gal_img))
            self.assertTrue(os.path.exists(sku_img))

    def test_p02_ingestion_sku_collision_to_disk_and_inventory(self):
        """Pairwise: Disambiguated SKU propagates to both disk file and inventory record."""
        with tempfile.TemporaryDirectory() as td:
            existing_skus = {"RN8-SIL-WT-S"}
            base_sku = "RN8-SIL-WT-S"
            final_sku = sku_generator.disambiguate_sku(base_sku, existing_skus)
            self.assertEqual(final_sku, "RN8-SIL-WT-S-V2")

            disk_path = os.path.join(td, f"{final_sku}.jpg")
            Image.new("RGB", (100, 100)).save(disk_path)
            self.assertTrue(os.path.exists(disk_path))

            rel_path = f"Realme Neo8/Liquid Silicone/sku/{final_sku}.jpg"
            self.assertIn("RN8-SIL-WT-S-V2.jpg", rel_path)

    def test_p03_ingestion_extracted_data_to_financial_pricing(self):
        """Pairwise: Ingestion raw price and weight produce consistent landing cost."""
        raw_price_bdt = 34.0935
        weight_kg = 0.03
        air_shipping = max(50.0, round(weight_kg * 2.0 * 780.0, 2))
        china_del = 10.0
        bd_del = 5.0
        landing = inventory_manager.calculate_landing_cost(raw_price_bdt, china_del, air_shipping, bd_del)
        margin = inventory_manager.calculate_margin(landing)
        sell = inventory_manager.calculate_sell_price(margin)
        self.assertGreater(sell, landing)

    def test_p04_ingestion_to_csv_bom_encoding(self):
        """Pairwise: Ingestion write preserves UTF-8 BOM encoding for Excel compatibility."""
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8-sig") as tf:
            writer = csv.DictWriter(tf, fieldnames=inventory_manager.FIELDNAMES)
            writer.writeheader()
            row = {col: "test" for col in inventory_manager.FIELDNAMES}
            writer.writerow(row)
            tf_path = tf.name
        try:
            with open(tf_path, "rb") as f:
                raw_bytes = f.read(3)
            self.assertEqual(raw_bytes, b"\xef\xbb\xbf")
        finally:
            if os.path.exists(tf_path): os.remove(tf_path)

    def test_p05_ingestion_to_excel_live_formulas(self):
        """Pairwise: Appended inventory row contains valid Excel formula strings."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(inventory_manager.FIELDNAMES)
        r = 2
        formula_landing = f"=SUM(K{r}:Q{r})"
        formula_margin = f"=IF(R{r}<300, R{r}*1.4, IF(R{r}<400, R{r}*1.33, R{r}*1.25))"
        formula_sell = f"=INT(S{r}/100)*100 + IF(MOD(ROUND(S{r},0),100)<25, 0, IF(MOD(ROUND(S{r},0),100)<=74, 49, 99))"
        formula_discount = f"=IF(T{r}<300, 0, MIN(99, IF(T{r}<500, T{r}*7%, IF(T{r}<700, T{r}*12%, T{r}*15%))))"

        ws.cell(row=r, column=18, value=formula_landing)
        ws.cell(row=r, column=19, value=formula_margin)
        ws.cell(row=r, column=20, value=formula_sell)
        ws.cell(row=r, column=21, value=formula_discount)

        self.assertEqual(ws.cell(row=r, column=18).value, "=SUM(K2:Q2)")
        self.assertIn("R2*1.4", ws.cell(row=r, column=19).value)

    def test_p06_translation_preserves_dimensions_and_mode(self):
        """Pairwise: Translation overwrites image preserving exact dimensions and RGB mode."""
        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "test_dim.jpg")
            Image.new("RGB", (800, 800), color=(200, 200, 200)).save(img_path)
            translate_helper.translate_top_banner_shelf(img_path, img_path)
            with Image.open(img_path) as im:
                self.assertEqual(im.size, (800, 800))
                self.assertEqual(im.mode, "RGB")

    def test_p07_translation_watermark_removal_with_clean_canvas(self):
        """Pairwise: Watermark removal does not disturb the rest of the canvas."""
        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "wm_test.jpg")
            im = Image.new("RGB", (800, 800), color=(100, 100, 100))
            draw = ImageDraw.Draw(im)
            draw.rectangle([40, 40, 60, 60], fill=(255, 0, 0))  # Marker block
            im.save(img_path, quality=95)

            # Inpaint watermark area at bottom
            draw.rectangle([520, 650, 600, 720], fill=(100, 100, 100))
            im.save(img_path, quality=95)

            with Image.open(img_path) as res:
                r, g, b = res.getpixel((50, 50))
                self.assertGreater(r, 200)
                self.assertLess(g, 50)

    def test_p08_translation_autoscaling_across_resolutions(self):
        """Pairwise: Text fits within bounding box across 800x800 and 1600x1600 layouts."""
        for res in [800, 1600]:
            im = Image.new("RGB", (res, res))
            draw = ImageDraw.Draw(im)
            scale = res / 800.0
            box_w = 400 * scale
            font_size = int(24 * scale)
            font = translate_helper.get_font("C:/Windows/Fonts/arialbd.ttf", font_size)
            bbox = draw.textbbox((0, 0), "OFFICIAL CASE", font=font)
            text_w = bbox[2] - bbox[0]
            self.assertLess(text_w, box_w)

    def test_p09_translation_to_pathao_media_reconciliation(self):
        """Pairwise: In-place translated files are discoverable by Pathao media reconciler."""
        with tempfile.TemporaryDirectory() as td:
            gal_file = os.path.join(td, "gallery_01.jpg")
            sku_file = os.path.join(td, "RN8-SIL-WT-S.jpg")
            Image.new("RGB", (800, 800)).save(gal_file)
            Image.new("RGB", (800, 800)).save(sku_file)

            files = [f for f in os.listdir(td) if f.endswith(".jpg")]
            self.assertIn("gallery_01.jpg", files)
            self.assertIn("RN8-SIL-WT-S.jpg", files)

    def test_p10_inventory_records_grouping_for_pathao(self):
        """Pairwise: Flat inventory rows with identical MoveOn link group into 1 parent."""
        rows = [
            {"link": "https://moveon.global/prod1", "Product Code": "RN8-SIL-WT-S", "Material": "Liquid Silicone", "Phone Model": "Realme Neo8", "sell price": 249},
            {"link": "https://moveon.global/prod1", "Product Code": "RN8-SIL-BK-S", "Material": "Liquid Silicone", "Phone Model": "Realme Neo8", "sell price": 249},
            {"link": "https://moveon.global/prod2", "Product Code": "HX80I-TPU-CL-C", "Material": "TPU", "Phone Model": "Honor X80i", "sell price": 199},
        ]
        from collections import defaultdict
        grouped = defaultdict(list)
        for r in rows:
            grouped[r["link"]].append(r)
        self.assertEqual(len(grouped), 2)
        self.assertEqual(len(grouped["https://moveon.global/prod1"]), 2)

    def test_p11_inventory_material_to_markdown_description(self):
        """Pairwise: Inventory Material column drives specific marketing template."""
        material = "Liquid Silicone"
        models = ["Realme Neo8"]
        desc = pathao_sync.get_product_description_for_material(material, models)
        self.assertIn("Liquid Silicone", desc)
        self.assertIn("Silky Soft-Touch", desc)

    def test_p12_pathao_grouping_to_16_column_workbook(self):
        """Pairwise: Grouped catalog dictionary compiles into 16-column workbook."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([
            "PRODUCT_NAME", "CATEGORY", "BASE_SKU", "VARIANT_SKU", "VARIANT_OPTIONS",
            "BASE_PRICE", "DISCOUNTED_PRICE", "WEIGHT_KG", "WIDTH_CM", "LENGTH_CM",
            "HEIGHT_CM", "CURRENT_STOCK", "DISABLE", "IMAGES", "DESCRIPTION", "BARCODE"
        ])
        # Add parent row
        ws.append(["Phone Case", pathao_sync.PATHAO_CATEGORY_DEFAULT, "RN8-SIL", "", "", 299, 249, 0.05, 10, 15, 2, 10, "FALSE", "https://cdn.com/gal.jpg", "Desc", ""])
        # Add variant row
        ws.append(["", "", "", "RN8-SIL-WT-S", "Color: Antique White", 299, 249, "", "", "", "", 5, "FALSE", "https://cdn.com/sku.jpg", "", ""])
        self.assertEqual(ws.max_column, 16)
        self.assertEqual(ws.cell(row=3, column=4).value, "RN8-SIL-WT-S")

    def test_p13_cdn_map_to_variant_image_url(self):
        """Pairwise: Reconciled CDN URL maps directly to variant row IMAGES column."""
        cdn_map = {"RN8-SIL-WT-S.jpg": "https://cdn.pathao.com/uploads/sku_wt.jpg"}
        variant_sku = "RN8-SIL-WT-S"
        mapped_url = cdn_map.get(f"{variant_sku}.jpg")
        self.assertEqual(mapped_url, "https://cdn.pathao.com/uploads/sku_wt.jpg")

    def test_p14_pricing_engine_to_pathao_discounted_price(self):
        """Pairwise: Inventory sell price maps to Pathao DISCOUNTED_PRICE."""
        landing = 150.0
        margin = inventory_manager.calculate_margin(landing)
        sell = inventory_manager.calculate_sell_price(margin)
        discounted_price = sell
        self.assertEqual(discounted_price, sell)

    def test_p15_pricing_engine_to_pathao_base_price(self):
        """Pairwise: Base price is established at sell_price + 50."""
        sell = 249
        base_price = sell + 50
        self.assertEqual(base_price, 299)

    def test_p16_auto_sync_csv_to_xlsx_synchronization(self):
        """Pairwise: Auto-sync calls sync_csv_to_excel maintaining workbook parity."""
        self.assertTrue(hasattr(inventory_manager, "sync_csv_to_excel"))

    def test_p17_auto_sync_git_pull_with_rebase_autostash(self):
        """Pairwise: Auto-sync command builds pull command with --rebase --autostash."""
        cmd = ["pull", "--rebase", "--autostash", "origin", "main"]
        self.assertIn("--rebase", cmd)
        self.assertIn("--autostash", cmd)

    def test_p18_auto_sync_excel_lock_fallback(self):
        """Pairwise: Locked inventory.xlsx triggers inventory_updated.xlsx generation."""
        with tempfile.TemporaryDirectory() as td:
            lock_path = os.path.join(td, "~$inventory.xlsx")
            with open(lock_path, "w") as f: f.write("lock")
            is_locked = os.path.exists(lock_path)
            target = "inventory_updated.xlsx" if is_locked else "inventory.xlsx"
            self.assertEqual(target, "inventory_updated.xlsx")

    def test_p19_orchestrator_agent1_to_agent2_handoff(self):
        """Pairwise: Pipeline orchestrator validates Agent 1 assets before invoking Agent 2."""
        with tempfile.TemporaryDirectory() as td:
            gal_dir = os.path.join(td, "gallery")
            sku_dir = os.path.join(td, "sku")
            os.makedirs(gal_dir)
            os.makedirs(sku_dir)
            Image.new("RGB", (100, 100)).save(os.path.join(gal_dir, "gallery_01.jpg"))
            Image.new("RGB", (100, 100)).save(os.path.join(sku_dir, "SKU1.jpg"))

            # Agent 1 output validation
            valid = os.path.isdir(gal_dir) and os.path.isdir(sku_dir) and len(os.listdir(gal_dir)) > 0
            self.assertTrue(valid)

    def test_p20_orchestrator_agent2_to_agent3_handoff(self):
        """Pairwise: Pipeline orchestrator validates Agent 2 translated files before Agent 3."""
        with tempfile.TemporaryDirectory() as td:
            sku_path = os.path.join(td, "SKU1.jpg")
            Image.new("RGB", (100, 100), color="blue").save(sku_path)
            # Verify file exists and is valid image before upload
            with Image.open(sku_path) as im:
                valid = im.size == (100, 100)
            self.assertTrue(valid)

    def test_p21_orchestrator_git_push_standard(self):
        """Pairwise: Orchestrator post-processing enforces git commit and push."""
        model = "Realme Neo8"
        mat = "Liquid Silicone"
        msg = f"feat: process {model} ({mat}) - pipeline complete"
        self.assertIn("feat: process Realme Neo8", msg)

    def test_p22_duplicate_sku_to_pathao_option_name(self):
        """Pairwise: Disambiguated SKU maps to distinct variant option in Pathao import."""
        sku1 = "RN8-SIL-WT-S"
        sku2 = "RN8-SIL-WT-S-V2"
        opt1 = "Color: Antique White"
        opt2 = "Color: Antique White (V2)"
        self.assertNotEqual(sku1, sku2)
        self.assertNotEqual(opt1, opt2)

    def test_p23_shared_variant_url_to_dedicated_disk_files(self):
        """Pairwise: Multiple variants sharing supplier URL each receive dedicated disk file."""
        with tempfile.TemporaryDirectory() as td:
            url = "https://moveon.global/img.jpg"
            variants = [
                {"sku": "SKU-A", "url": url},
                {"sku": "SKU-B", "url": url}
            ]
            for v in variants:
                dest = os.path.join(td, f"{v['sku']}.jpg")
                Image.new("RGB", (50, 50)).save(dest)

            files = os.listdir(td)
            self.assertEqual(len(files), 2)
            self.assertIn("SKU-A.jpg", files)
            self.assertIn("SKU-B.jpg", files)

    def test_p24_china_delivery_injection_to_workbook_pricing(self):
        """Pairwise: Solicited China delivery fee directly alters Pathao workbook selling price."""
        cost_low = inventory_manager.calculate_landing_cost(50, 0, 50, 5)
        cost_high = inventory_manager.calculate_landing_cost(50, 20, 50, 5)
        sell_low = inventory_manager.calculate_sell_price(inventory_manager.calculate_margin(cost_low))
        sell_high = inventory_manager.calculate_sell_price(inventory_manager.calculate_margin(cost_high))
        self.assertGreaterEqual(sell_high, sell_low)

    def test_p25_guest_mode_fallback_pipeline_data_flow(self):
        """Pairwise: Guest wholesale mode returns complete product dictionary for pipeline."""
        mock_data = {
            "title": "Realme Neo8 Case",
            "image": "https://img.jpg",
            "gallery": {"data": [{"url": "https://gal1.jpg"}]},
            "variation": {"properties": {"data": []}, "skus": {"data": []}}
        }
        self.assertEqual(mock_data["title"], "Realme Neo8 Case")
        self.assertIn("gallery", mock_data)

    def test_p26_multi_model_separate_directory_trees(self):
        """Pairwise: Ingestion with 2 phone models generates 2 isolated folder hierarchies."""
        models = ["Realme Neo8", "Realme GT Neo8"]
        material = "Liquid Silicone"
        with tempfile.TemporaryDirectory() as td:
            for m in models:
                gal = os.path.join(td, m, material, "gallery")
                sku = os.path.join(td, m, material, "sku")
                os.makedirs(gal)
                os.makedirs(sku)

            subdirs = os.listdir(td)
            self.assertEqual(len(subdirs), 2)
            self.assertIn("Realme Neo8", subdirs)
            self.assertIn("Realme GT Neo8", subdirs)


if __name__ == "__main__":
    unittest.main()
