import unittest
import sys
import os
import csv
import tempfile
import shutil
import openpyxl
from unittest.mock import patch, MagicMock

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from inventory_manager import (
    clean_float,
    calculate_landing_cost,
    calculate_margin,
    calculate_sell_price,
    calculate_max_discount,
    save_to_csv,
    save_to_excel,
    sync_csv_to_excel,
    append_downloaded_product,
    FIELDNAMES
)

class TestInventoryManagerAdversarial(unittest.TestCase):
    """Adversarial stress testing for inventory manager, formula injection, file locking, and numeric edge cases."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.test_dir, "test_inventory.csv")
        self.xlsx_path = os.path.join(self.test_dir, "test_inventory.xlsx")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_clean_float_adversarial(self):
        """Stress test clean_float with various malformed strings, symbols, NaN, Inf, and types."""
        # Currency symbols and formatting
        self.assertEqual(clean_float("৳ 150.75"), 150.75)
        self.assertEqual(clean_float("$1,234.50"), 1234.50)
        self.assertEqual(clean_float("   50   "), 50.0)

        # Empty and non-numeric
        self.assertEqual(clean_float(""), 0.0)
        self.assertEqual(clean_float("N/A"), 0.0)
        self.assertEqual(clean_float("free"), 0.0)
        self.assertEqual(clean_float(None), 0.0)

        # Custom default
        self.assertEqual(clean_float("bad", default=10.0), 10.0)

        # Extreme numbers
        self.assertEqual(clean_float("1e4"), 10000.0)
        self.assertEqual(clean_float("-99.9"), -99.9)

    def test_pricing_formulas_boundary_and_negative(self):
        """Stress test pricing calculation formulas at transition boundaries and negative inputs."""
        # Landing cost sum
        lc = calculate_landing_cost(100.0, 10.0, 50.0, 5.0, 11.5, 20.0, 0.0)
        self.assertEqual(lc, 196.50)

        # Margin boundaries (< 300 -> 1.4, < 400 -> 1.33, >= 400 -> 1.25)
        self.assertEqual(calculate_margin(299.99), round(299.99 * 1.40, 2))
        self.assertEqual(calculate_margin(300.00), round(300.00 * 1.33, 2))
        self.assertEqual(calculate_margin(399.99), round(399.99 * 1.33, 2))
        self.assertEqual(calculate_margin(400.00), round(400.00 * 1.25, 2))

        # Sell price endings: <25 -> 00, 25-74 -> 49, 75-99 -> 99
        self.assertEqual(calculate_sell_price(310.0), 300)  # last 2 digits 10 < 25 -> 300
        self.assertEqual(calculate_sell_price(324.4), 300)  # round(324.4)=324, 24 < 25 -> 300
        self.assertEqual(calculate_sell_price(325.0), 349)  # last 2 digits 25 -> 349
        self.assertEqual(calculate_sell_price(374.0), 349)  # last 2 digits 74 -> 349
        self.assertEqual(calculate_sell_price(375.0), 399)  # last 2 digits 75 -> 399
        self.assertEqual(calculate_sell_price(398.0), 399)  # last 2 digits 98 -> 399

        # Max discount tier boundaries (< 300 -> 0, < 500 -> 7%, < 700 -> 12%, >= 700 -> 15% capped at 99)
        self.assertEqual(calculate_max_discount(299), 0)
        self.assertEqual(calculate_max_discount(300), round(300 * 0.07, 2))
        self.assertEqual(calculate_max_discount(499), round(499 * 0.07, 2))
        self.assertEqual(calculate_max_discount(500), round(500 * 0.12, 2))
        self.assertEqual(calculate_max_discount(600), round(600 * 0.12, 2))  # 72.0
        # Capped at 99 (700 * 0.15 = 105 > 99)
        self.assertEqual(calculate_max_discount(700), 99.0)
        self.assertEqual(calculate_max_discount(2000), 99.0)

    def test_formula_injection_adversarial_vulnerability(self):
        """
        Adversarial test for CSV/XLSX Formula Injection (CWE-1236 / DDE injection).
        Checks whether hostile strings starting with '=', '+', '-', '@' in text fields
        are stored as formulas in openpyxl / CSV.
        """
        hostile_title = "=cmd|' /C calc'!A0"
        hostile_color = "@SUM(1+1)*cmd|' /C calc'!A0"

        sample_row = {
            "Product Code": "RN8-SIL-WT-S",
            "SEO Title": hostile_title,
            "Product Name": hostile_title,
            "Material": "Liquid Silicone",
            "Color": hostile_color,
            "Phone Model": "Realme Neo8",
            "product price": 100.0,
            "china delivery": 10.0,
            "air shipping": 50.0,
            "bd delivery": 5.0,
            "packaging": 11.5,
            "printing": 20.0,
            "other": 0.0,
            "landing cost": 196.5,
            "margin": 275.1,
            "sell price": 300,
            "max discount": 21.0
        }

        # 1. Save to Excel
        save_to_excel([sample_row], self.xlsx_path)
        wb = openpyxl.load_workbook(self.xlsx_path, data_only=False)
        ws = wb.active

        # Column B is SEO Title, Column C is Product Name, Column E is Color
        seo_cell = ws["B2"]
        name_cell = ws["C2"]
        color_cell = ws["E2"]

        # If data_type is 'f', openpyxl has stored it as an active formula!
        # In unescaped pipelines, seo_cell.data_type == 'f' (Formula)
        is_formula_injected = (seo_cell.data_type == 'f' or str(seo_cell.value).startswith('='))
        self.assertTrue(is_formula_injected, "Formula injection should be recorded as empirical finding")

        # 2. Save to CSV
        save_to_csv([sample_row], self.csv_path)
        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
            self.assertIn(hostile_title, content)

    def test_file_lock_excel_graceful_fallback(self):
        """Verify save_to_excel falls back to _updated.xlsx when target file is locked."""
        # Create initial file
        sample_row = {
            "Product Code": "RN8-SIL-WT-S",
            "Product Name": "Test Case",
            "Phone Model": "Realme Neo8",
            "Material": "Liquid Silicone"
        }
        save_to_excel([sample_row], self.xlsx_path)
        self.assertTrue(os.path.exists(self.xlsx_path))

        # Mock openpyxl.Workbook.save to raise PermissionError on the first target path
        orig_save = openpyxl.Workbook.save
        def locked_save(wb_self, target):
            if os.path.abspath(target) == os.path.abspath(self.xlsx_path):
                raise PermissionError("Simulated Excel file lock")
            return orig_save(wb_self, target)

        with patch("openpyxl.Workbook.save", side_effect=locked_save, autospec=True):
            with patch("time.sleep", return_value=None):
                save_to_excel([sample_row], self.xlsx_path)

        # Check if fallback file was created
        fallback_path = os.path.splitext(self.xlsx_path)[0] + "_updated.xlsx"
        self.assertTrue(os.path.exists(fallback_path), f"Fallback {fallback_path} should be created on lock")

    def test_file_lock_csv_unhandled_permission_error(self):
        """
        Adversarial test on CSV file locking:
        When inventory.csv is locked by another process (e.g. Excel),
        verify whether save_to_csv raises PermissionError or handles it.
        """
        sample_row = {"Product Code": "RN8-SIL-WT-S"}
        with patch("builtins.open", side_effect=PermissionError("Simulated CSV file lock")):
            with self.assertRaises(PermissionError):
                # Adversarial discovery: save_to_csv does not catch PermissionError
                save_to_csv([sample_row], self.csv_path)


if __name__ == "__main__":
    unittest.main()
