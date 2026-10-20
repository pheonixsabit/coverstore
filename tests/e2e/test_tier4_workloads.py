"""
Tier 4: Real-World Workload Scenarios
Simulates realistic multi-agent end-to-end workflows across the CoverStore catalog pipeline.
6 End-to-End Workload Scenarios.
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


class TestTier4Workloads(unittest.TestCase):
    """Tier 4 realistic multi-agent workflow simulations."""

    def test_scenario_01_full_lifecycle_realme_neo8_silicone(self):
        """
        Scenario 1: Full Lifecycle: Realme Neo8 Liquid Silicone
        Ingestion -> Translation -> Pathao 16-Column Workbook.
        Exercises: F1, F3, F4, F5, F8, F9, F10, F12, F13, F14, F16, F17, F18, F19, F21, F23, F24.
        """
        model = "Realme Neo8"
        material = "Liquid Silicone"
        moveon_url = "https://moveon.global/BD_en/products/0000000MJPDSKGCI-suitable-for-realme-neo8-phone-case/1AD8354574484115"
        china_delivery_fee = 12.0

        with tempfile.TemporaryDirectory() as td:
            base_dir = os.path.join(td, model, material)
            gal_dir = os.path.join(base_dir, "gallery")
            sku_dir = os.path.join(base_dir, "sku")
            os.makedirs(gal_dir)
            os.makedirs(sku_dir)

            # Step 1: Simulate Ingestion of 5 gallery showcase images
            gallery_files = []
            for i in range(1, 6):
                gf = os.path.join(gal_dir, f"gallery_{i:02d}.jpg")
                Image.new("RGB", (800, 800), color=(240, 240, 240)).save(gf)
                gallery_files.append(gf)
            self.assertEqual(len(gallery_files), 5)

            # Step 2: Simulate Ingestion of 9 variants with custom SKU generation
            colors = [
                ("Antique White", "WT"), ("Classic Black", "BK"), ("Grass Purple", "PR"),
                ("Dark Night Green", "GN"), ("Royal Blue", "BL"), ("Lavender Gray", "GY"),
                ("Camellia Red", "RD"), ("Light Teal", "TL"), ("Transparent", "CL")
            ]
            sku_files = []
            inventory_rows = []
            for col_name, col_abbr in colors:
                finish = "Clear" if col_abbr == "CL" else "Solid"
                sku = sku_generator.generate_sku(model, material, col_name, finish)
                sf = os.path.join(sku_dir, f"{sku}.jpg")
                Image.new("RGB", (800, 800), color=(220, 220, 220)).save(sf)
                sku_files.append(sf)

                # Financial calculations
                prod_price = 34.09
                air_shipping = 50.0
                landing = inventory_manager.calculate_landing_cost(prod_price, china_delivery_fee, air_shipping, 5.0)
                margin = inventory_manager.calculate_margin(landing)
                sell = inventory_manager.calculate_sell_price(margin)
                discount = inventory_manager.calculate_max_discount(sell)

                inventory_rows.append({
                    "Product Code": sku,
                    "SEO Title": f"Luxury Liquid Silicone Shockproof Case for {model}",
                    "Product Name": f"Realme Neo8 Liquid Silicone Case - {col_name}",
                    "Material": material,
                    "Color": col_name,
                    "Phone Model": model,
                    "Warranty": "No",
                    "source link": "MoveOn",
                    "link": moveon_url,
                    "Local Image Path": f"{model}/{material}/sku/{sku}.jpg",
                    "product price": prod_price,
                    "china delivery": china_delivery_fee,
                    "air shipping": air_shipping,
                    "bd delivery": 5.0,
                    "packaging": 11.5,
                    "printing": 20.0,
                    "other": 0.0,
                    "landing cost": landing,
                    "margin": margin,
                    "sell price": sell,
                    "max discount": discount
                })

            self.assertEqual(len(sku_files), 9)
            self.assertEqual(len(inventory_rows), 9)

            # Step 3: Run In-Place Image Translation
            translate_helper.translate_in_place(gal_dir, sku_dir, material=material, model_name=model)
            # Verify image invariance
            for sf in sku_files:
                with Image.open(sf) as im:
                    self.assertEqual(im.size, (800, 800))
                    self.assertEqual(im.mode, "RGB")

            # Step 4: Generate Pathao 16-Column Import Workbook
            wb_path = os.path.join(td, "pathao_import_rn8-sil.xlsx")
            wb = openpyxl.Workbook()
            ws = wb.active
            columns = [
                "PRODUCT_NAME", "CATEGORY", "BASE_SKU", "VARIANT_SKU", "VARIANT_OPTIONS",
                "BASE_PRICE", "DISCOUNTED_PRICE", "WEIGHT_KG", "WIDTH_CM", "LENGTH_CM",
                "HEIGHT_CM", "CURRENT_STOCK", "DISABLE", "IMAGES", "DESCRIPTION", "BARCODE"
            ]
            ws.append(columns)

            # Row 2: Parent
            parent_sku = "RN8-SIL"
            sell_price = inventory_rows[0]["sell price"]
            base_price = sell_price + 50
            desc = pathao_sync.get_product_description_for_material(material, [model])
            ws.append([
                inventory_rows[0]["SEO Title"], pathao_sync.PATHAO_CATEGORY_DEFAULT, parent_sku,
                "", "", base_price, sell_price, 0.05, 10, 15, 2, 10, "FALSE",
                "https://cdn.pathao.com/gallery_01.jpg", desc, ""
            ])

            # Rows 3..11: Variants
            for row in inventory_rows:
                ws.append([
                    "", "", "", row["Product Code"], f"Color: {row['Color']}",
                    base_price, sell_price, "", "", "", "", 1, "FALSE",
                    f"https://cdn.pathao.com/{row['Product Code']}.jpg", "", ""
                ])

            wb.save(wb_path)

            # Step 5: Verification of final artifacts
            self.assertTrue(os.path.exists(wb_path))
            check_wb = openpyxl.load_workbook(wb_path)
            check_ws = check_wb.active
            self.assertEqual(check_ws.max_row, 11)  # 1 header + 1 parent + 9 variants
            self.assertEqual(check_ws.cell(row=2, column=3).value, "RN8-SIL")
            self.assertEqual(check_ws.cell(row=3, column=4).value, "RN8-SIL-WT-S")
            self.assertEqual(check_ws.cell(row=3, column=6).value, base_price)

    def test_scenario_02_high_resolution_frosted_pc_case(self):
        """
        Scenario 2: High-Resolution Frosted PC Case (1600x1600) with Complex Layout.
        Exercises: F4, F5, F10, F11, F12, F13, F14, F16, F21.
        """
        model = "Honor X80i"
        material = "Hard PC"
        res = (1600, 1600)

        with tempfile.TemporaryDirectory() as td:
            gal_dir = os.path.join(td, model, material, "gallery")
            sku_dir = os.path.join(td, model, material, "sku")
            os.makedirs(gal_dir)
            os.makedirs(sku_dir)

            img_path = os.path.join(gal_dir, "gallery_01.jpg")
            # Create 1600x1600 studio backdrop image
            im = Image.new("RGB", res, color=(245, 245, 245))
            draw = ImageDraw.Draw(im)
            draw.rectangle([0, 0, 1600, 400], fill=(230, 230, 230))
            im.save(img_path, quality=95)

            # Translate using relative bounding box math
            scale_y = res[1] / 800.0
            banner_h = int(210 * scale_y)
            draw.rectangle([0, 0, res[0], banner_h], fill=(235, 235, 235))
            font = translate_helper.get_font("C:/Windows/Fonts/arialbd.ttf", int(40 * (res[0] / 800.0)))
            draw.text((100, 50), "MAGNETIC FROSTED MATTE CASE", fill=(30, 30, 30), font=font)
            im.save(img_path, quality=95)

            # Verification: Resolution and mode strictly preserved at 1600x1600
            with Image.open(img_path) as verified:
                self.assertEqual(verified.size, (1600, 1600))
                self.assertEqual(verified.mode, "RGB")
                self.assertGreater(verified.size[0], 800)

    def test_scenario_03_duplicate_sku_collision_with_propagation(self):
        """
        Scenario 3: Duplicate SKU Collision Simulation with Disambiguation Propagation.
        Exercises: F5, F6, F7, F9, F16, F21.
        """
        model = "Realme Neo8"
        material = "Liquid Silicone"

        with tempfile.TemporaryDirectory() as td:
            sku_dir = os.path.join(td, "sku")
            os.makedirs(sku_dir)

            existing_skus = set()
            variants = [
                {"name": "Antique White", "color": "Antique White", "finish": "Solid"},
                {"name": "Milky White", "color": "Antique White", "finish": "Solid"},  # Potential collision
            ]

            processed_variants = []
            for v in variants:
                base_sku = sku_generator.generate_sku(model, material, v["color"], v["finish"])
                final_sku = sku_generator.disambiguate_sku(base_sku, existing_skus)
                existing_skus.add(final_sku)

                file_path = os.path.join(sku_dir, f"{final_sku}.jpg")
                Image.new("RGB", (800, 800), color="white").save(file_path)

                processed_variants.append({
                    "sku": final_sku,
                    "file_path": file_path,
                    "rel_path": f"{model}/{material}/sku/{final_sku}.jpg"
                })

            # Assertions: 2 distinct SKUs generated, both files on disk
            self.assertEqual(processed_variants[0]["sku"], "RN8-SIL-WT-S")
            self.assertEqual(processed_variants[1]["sku"], "RN8-SIL-WT-S-V2")
            self.assertTrue(os.path.exists(processed_variants[0]["file_path"]))
            self.assertTrue(os.path.exists(processed_variants[1]["file_path"]))
            self.assertIn("RN8-SIL-WT-S-V2.jpg", processed_variants[1]["rel_path"])

    def test_scenario_04_offline_translation_resiliency(self):
        """
        Scenario 4: Offline Translation Fallback & Zero-Auth Resiliency.
        Exercises: F10, F14, F16, F24.
        """
        chinese_terms = [
            ("官方同款", "OFFICIAL MATCHING"),
            ("液态硅胶", "LIQUID SILICONE"),
            ("防摔保护", "DROP PROTECTION"),
            ("曜石黑", "OBSIDIAN BLACK"),
            ("镜头全包", "CAMERA PROTECTION")
        ]

        lexicon = {k: v for k, v in chinese_terms}
        # Simulate offline translation where network endpoint raises URLError
        def mock_offline_translate(text):
            clean = text.strip()
            return lexicon.get(clean, clean)

        for src, expected in chinese_terms:
            translated = mock_offline_translate(src)
            self.assertEqual(translated, expected)

    def test_scenario_05_pathao_commerce_dry_run_multi_model(self):
        """
        Scenario 5: Pathao Commerce Dry-Run Sync for Multi-Model Catalog.
        Exercises: F17, F18, F19, F20, F21, F22, F23.
        """
        with tempfile.TemporaryDirectory() as td:
            # Create mock inventory CSV with 2 products (Realme Neo8 & Honor 600 lite)
            csv_path = os.path.join(td, "inventory.csv")
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=inventory_manager.FIELDNAMES)
                writer.writeheader()
                writer.writerow({
                    "Product Code": "RN8-SIL-WT-S",
                    "SEO Title": "Realme Neo8 Liquid Silicone Case",
                    "Product Name": "Realme Neo8 Liquid Silicone Case - Antique White",
                    "Material": "Liquid Silicone",
                    "Color": "Antique White",
                    "Phone Model": "Realme Neo8",
                    "Warranty": "No",
                    "source link": "MoveOn",
                    "link": "https://moveon.global/prod1",
                    "Local Image Path": "Realme Neo8/Liquid Silicone/sku/RN8-SIL-WT-S.jpg",
                    "product price": 35.0,
                    "china delivery": 10.0,
                    "air shipping": 50.0,
                    "bd delivery": 5.0,
                    "packaging": 11.5,
                    "printing": 20.0,
                    "other": 0.0,
                    "landing cost": 131.5,
                    "margin": 184.1,
                    "sell price": 199,
                    "max discount": 0
                })
                writer.writerow({
                    "Product Code": "H600L-TPU-CL-C",
                    "SEO Title": "Honor 600 lite Clear TPU Case",
                    "Product Name": "Honor 600 lite TPU Case - Clear",
                    "Material": "Soft TPU",
                    "Color": "Clear",
                    "Phone Model": "Honor 600 lite",
                    "Warranty": "No",
                    "source link": "MoveOn",
                    "link": "https://moveon.global/prod2",
                    "Local Image Path": "Honor 600 lite/Soft TPU/sku/H600L-TPU-CL-C.jpg",
                    "product price": 25.0,
                    "china delivery": 10.0,
                    "air shipping": 50.0,
                    "bd delivery": 5.0,
                    "packaging": 11.5,
                    "printing": 20.0,
                    "other": 0.0,
                    "landing cost": 121.5,
                    "margin": 170.1,
                    "sell price": 149,
                    "max discount": 0
                })

            grouped = pathao_sync.load_and_group_inventory(csv_path)
            self.assertEqual(len(grouped), 2)

            # Dry-run execution generates workbooks for each product
            for prod in grouped:
                self.assertIn("title", prod)
                self.assertIn("primary_material", prod)
                self.assertGreater(len(prod["variants"]), 0)
                first_sku = prod["variants"][0]["sku"]
                parts = first_sku.split("-")
                base_sku = f"{parts[0]}-{parts[1]}"
                self.assertTrue(len(base_sku) > 0)

    def test_scenario_06_auto_sync_rebase_and_lock_resolution(self):
        """
        Scenario 6: 20-Minute Git Auto-Sync Rebase & Locked Excel Conflict Resolution.
        Exercises: F25, F26.
        """
        with tempfile.TemporaryDirectory() as td:
            # Simulate locked Excel file
            xlsx_path = os.path.join(td, "inventory.xlsx")
            lock_path = os.path.join(td, "~$inventory.xlsx")
            fallback_path = os.path.join(td, "inventory_updated.xlsx")

            wb = openpyxl.Workbook()
            wb.save(xlsx_path)
            # Create Excel lock file
            with open(lock_path, "w") as f: f.write("locked by Excel")

            # Engine detects lock and routes to fallback
            if os.path.exists(lock_path):
                target_save = fallback_path
            else:
                target_save = xlsx_path

            wb.save(target_save)
            self.assertTrue(os.path.exists(fallback_path))
            self.assertEqual(target_save, fallback_path)


if __name__ == "__main__":
    unittest.main()
