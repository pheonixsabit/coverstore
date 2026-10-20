#!/usr/bin/env python3
"""
Adversarial Stress Test Suite - Challenger 2 (Tier 5 Hardening)
Empirical challenge suite for:
  1. Pathao Commerce Integration (scripts/pathao_sync.py)
  2. Offline Fault Tolerance & Lexicon Fallback (scripts/image_translator.py)
  3. Git Auto-Sync & Concurrency Safety (scripts/auto_sync.py & scripts/pipeline_orchestrator.py)
"""

import os
import sys
import unittest
import tempfile
import shutil
import json
import csv
import io
import re
import socket
import subprocess
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

import openpyxl
from PIL import Image

# Ensure project scripts are importable
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import pathao_sync
from pathao_sync import (
    PathaoCommerceClient,
    generate_import_workbook,
    load_and_group_inventory,
    get_product_description_for_material,
    IMPORT_COLUMNS
)
import image_translator
from image_translator import ImageTranslator, DOMAIN_LEXICON
import auto_sync
from auto_sync import perform_sync, run_git
import pipeline_orchestrator
from pipeline_orchestrator import git_commit_and_push, PipelineOrchestrator


class TestPathaoSyncAdversarial(unittest.TestCase):
    """Stress tests scripts/pathao_sync.py under adversarial inputs and session states."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="adv_pathao_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_corrupted_session_empty_file(self):
        """Adversarial session test: 0-byte .pathao_session.json."""
        session_file = os.path.join(self.temp_dir, ".pathao_session.json")
        with open(session_file, "w") as f:
            pass  # 0 bytes

        client = PathaoCommerceClient(headless=True, session_path=session_file)
        # Should not raise exception when starting/checking session
        try:
            with patch("playwright.sync_api.sync_playwright") as mock_pw:
                mock_browser = MagicMock()
                mock_context = MagicMock()
                mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser
                mock_browser.new_context.return_value = mock_context
                client.start()
                # Verify that storage_state was NOT added to new_context options
                call_kwargs = mock_browser.new_context.call_args[1]
                self.assertNotIn("storage_state", call_kwargs)
        finally:
            client.close()

    def test_corrupted_session_syntax_error(self):
        """Adversarial session test: Malformed JSON syntax in session file."""
        session_file = os.path.join(self.temp_dir, ".pathao_session.json")
        with open(session_file, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true, unterminated...")

        client = PathaoCommerceClient(headless=True, session_path=session_file)
        try:
            with patch("playwright.sync_api.sync_playwright") as mock_pw:
                mock_browser = MagicMock()
                mock_context = MagicMock()
                mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser
                mock_browser.new_context.return_value = mock_context
                client.start()
                call_kwargs = mock_browser.new_context.call_args[1]
                self.assertNotIn("storage_state", call_kwargs)
        finally:
            client.close()

    def test_corrupted_session_unexpected_data_type(self):
        """Adversarial session test: JSON containing top-level list or int instead of dict."""
        for invalid_content in ["[1, 2, 3]", "12345", '"string_payload"']:
            session_file = os.path.join(self.temp_dir, ".pathao_session.json")
            with open(session_file, "w", encoding="utf-8") as f:
                f.write(invalid_content)

            client = PathaoCommerceClient(headless=True, session_path=session_file)
            try:
                with patch("playwright.sync_api.sync_playwright") as mock_pw:
                    mock_browser = MagicMock()
                    mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser
                    mock_browser.new_context.return_value = MagicMock()
                    # Must not crash with AttributeError
                    client.start()
                    call_kwargs = mock_browser.new_context.call_args[1]
                    self.assertNotIn("storage_state", call_kwargs)
            finally:
                client.close()

    def test_inventory_missing_and_empty_csv(self):
        """Adversarial inventory test: Missing CSV, 0-byte CSV, or empty rows."""
        # Non-existent file
        non_existent = os.path.join(self.temp_dir, "non_existent.csv")
        res = load_and_group_inventory(non_existent)
        self.assertEqual(res, [])

        # 0-byte CSV
        empty_csv = os.path.join(self.temp_dir, "empty.csv")
        with open(empty_csv, "w", encoding="utf-8") as f:
            pass
        res = load_and_group_inventory(empty_csv)
        self.assertEqual(res, [])

        # CSV with header only, 0 rows
        header_only = os.path.join(self.temp_dir, "header_only.csv")
        with open(header_only, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["link", "Product Code", "Phone Model", "Material", "sell price"])
        res = load_and_group_inventory(header_only)
        self.assertEqual(res, [])

    def test_inventory_corrupted_data_types(self):
        """Adversarial inventory test: Malformed prices, commas, negative prices, None fields."""
        csv_path = os.path.join(self.temp_dir, "corrupted_inventory.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["link", "Product Code", "Phone Model", "Material", "Color", "sell price", "Local Image Path"])
            writer.writerow(["https://moveon.global/item1", "RN8-SIL-WT-S", "Realme Neo8", "Liquid Silicone", "White", "INVALID_PRICE", ""])
            writer.writerow(["https://moveon.global/item1", "RN8-SIL-BK-S", "Realme Neo8", "Liquid Silicone", "Black", "৳ 550.00", ""])
            writer.writerow(["https://moveon.global/item1", "RN8-SIL-PR-S", "Realme Neo8", "Liquid Silicone", "Purple", "-100", ""])
            writer.writerow(["", "EMPTY-LINK-SKU", "Realme Neo8", "Liquid Silicone", "Clear", "300", ""])

        products = load_and_group_inventory(csv_path)
        self.assertEqual(len(products), 1)  # Empty link is skipped
        variants = products[0]["variants"]
        self.assertEqual(len(variants), 3)

        # Fallback price verification
        self.assertEqual(variants[0]["price"], 349)  # Fallback from INVALID_PRICE
        self.assertEqual(variants[1]["price"], 550)  # Parsed from currency string
        self.assertEqual(variants[2]["price"], -100) # Negative int preserved

    def test_workbook_special_characters_and_emojis(self):
        """Adversarial workbook test: Unicode emojis, XML entities, newlines, and quotes."""
        product = {
            "title": "Special Case <Test> & 'Chars' \"Quotes\" 📱✨🔥",
            "phone_models": ["Realme Neo8 & Pro"],
            "primary_material": "Liquid Silicone / 硅胶",
            "description": "Line 1\nLine 2\tTabbed\nSpecial chars: <div class='test'>&amp;</div> ✨🎉",
            "gallery_images": ["gallery_01.jpg"],
            "variants": [
                {
                    "sku": "RN8-SIL-WT-S-V1",
                    "phone_model": "Realme Neo8",
                    "color": "Antique White / 古董白 🤍",
                    "price": 349,
                    "stock": 1,
                    "image_path": "RN8-SIL-WT-S-V1.jpg"
                }
            ]
        }
        out_path = os.path.join(self.temp_dir, "special_chars_import.xlsx")
        generate_import_workbook(product, output_path=out_path)

        self.assertTrue(os.path.exists(out_path))
        wb = openpyxl.load_workbook(out_path)
        ws = wb.active
        self.assertEqual(ws.max_row, 2)  # Header + 1 variant + parent = 2 data rows

        # Validate parent description and title
        parent_title = ws.cell(row=2, column=2).value
        parent_desc = ws.cell(row=2, column=16).value
        variant_opt = ws.cell(row=3, column=6).value

        self.assertIn("Special Case <Test>", parent_title)
        self.assertIn("Line 1\nLine 2", parent_desc)
        self.assertIn("✨🎉", parent_desc)
        self.assertIn("(V1)", variant_opt)
        wb.close()

    def test_workbook_scale_50_plus_variants(self):
        """Adversarial scalability test: Generating workbook with 60 distinct variants."""
        variants = []
        for i in range(1, 61):
            variants.append({
                "sku": f"RN8-SIL-C{i:02d}-S",
                "phone_model": "Realme Neo8",
                "color": f"Color Variant {i}",
                "price": 300 + i,
                "stock": 5,
                "image_path": f"RN8-SIL-C{i:02d}-S.jpg"
            })

        product = {
            "title": "Realme Neo8 Massive 60-Variant Collection",
            "phone_models": ["Realme Neo8"],
            "primary_material": "Liquid Silicone",
            "description": "Massive variant catalog stress test.",
            "gallery_images": [f"gallery_{g:02d}.jpg" for g in range(1, 11)],
            "variants": variants
        }

        out_path = os.path.join(self.temp_dir, "massive_60_variants.xlsx")
        generate_import_workbook(product, output_path=out_path)

        self.assertTrue(os.path.exists(out_path))
        wb = openpyxl.load_workbook(out_path)
        ws = wb.active
        # Header (row 1) + Parent Product (row 2) + 60 Variants (rows 3..62) = 62 rows
        self.assertEqual(ws.max_row, 62)
        self.assertEqual(ws.max_column, 16)

        # Verify parent row
        self.assertEqual(ws.cell(row=2, column=4).value, "RN8-SIL")
        self.assertEqual(len(ws.cell(row=2, column=15).value.split(",")), 10)  # 10 gallery images

        # Verify last variant row
        self.assertEqual(ws.cell(row=62, column=5).value, "RN8-SIL-C60-S")
        self.assertEqual(ws.cell(row=62, column=6).value, "Color: Color Variant 60")
        self.assertEqual(ws.cell(row=62, column=8).value, 360)
        wb.close()

    def test_extreme_disambiguation_formatting(self):
        """Adversarial option label test: Extreme suffix codes (-V10, -V99, non-numeric)."""
        test_cases = [
            ("RN8-SIL-WT-S-V1", "Antique White", "Color: Antique White (V1)"),
            ("RN8-SIL-WT-S-V2", "Antique White", "Color: Antique White (V2)"),
            ("RN8-SIL-WT-S-V10", "Antique White", "Color: Antique White (V10)"),
            ("RN8-SIL-WT-S-V99", "Antique White", "Color: Antique White (V99)"),
            ("RN8-SIL-WT-S-V2", "Antique White (V2)", "Color: Antique White (V2)"), # Avoid duplicate (V2) (V2)
        ]

        for sku, color, expected_opt in test_cases:
            product = {
                "title": "Disambiguation Test",
                "variants": [{
                    "sku": sku,
                    "color": color,
                    "price": 349,
                    "stock": 1,
                    "image_path": ""
                }]
            }
            out_path = os.path.join(self.temp_dir, f"test_{sku}.xlsx")
            generate_import_workbook(product, output_path=out_path)
            wb = openpyxl.load_workbook(out_path)
            ws = wb.active
            actual_opt = ws.cell(row=3, column=6).value
            self.assertEqual(actual_opt, expected_opt)
            wb.close()


class TestOfflineResilienceAdversarial(unittest.TestCase):
    """Stress tests offline translation resilience and network failure degradation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="adv_offline_")
        self.translator = ImageTranslator(timeout=2)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_offline_lexicon_exact_without_network(self):
        """Ensures known terms resolve instantly with zero network calls."""
        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = AssertionError("Network should NOT be accessed for known lexicon terms!")
            # 10 core terms from domain lexicon
            terms = [
                ("液态硅胶", "Liquid Silicone"),
                ("曜石黑", "Obsidian Black"),
                ("古董白", "Antique White"),
                ("远峰蓝", "Sierra Blue"),
                ("暗夜绿", "Dark Night Green"),
                ("全包防摔", "All-Inclusive Shockproof"),
                ("超薄散热", "Ultra-Thin Cooling"),
                ("亲肤手感", "Skin-Friendly Feel"),
                ("真机开模", "1:1 Precision Mold"),
                ("磁吸无线充", "Magnetic Wireless Charging"),
            ]
            for zh, expected_en in terms:
                result = self.translator.translate_text(zh)
                self.assertEqual(result, expected_en)

    def test_offline_compound_terms_token_fallback(self):
        """Ensures compound phrases degrade gracefully to Tier 3 token replacement when offline."""
        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = urllib.error.URLError("DNS lookup failed: Offline mode")

            # Compound text with multiple lexicon terms
            compound = "全新 液态硅胶 经典黑 防摔壳"
            translated = self.translator.translate_text(compound)
            # Should contain translated lexicon tokens
            self.assertIn("Liquid Silicone", translated)
            self.assertIn("Classic Black", translated)
            self.assertIn("Shockproof Case", translated)

    def test_offline_unknown_text_does_not_crash(self):
        """Ensures entirely novel Chinese text gracefully returns when offline without crashing."""
        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = socket.gaierror(-3, "Temporary failure in name resolution")

            unknown_text = "完全未知的测试文字"
            result = self.translator.translate_text(unknown_text)
            self.assertIsInstance(result, str)
            self.assertEqual(result, unknown_text)

    def test_offline_directory_translation_invariance(self):
        """Empirically verifies in-place directory translation with simulated total network outage."""
        gal_dir = os.path.join(self.temp_dir, "gallery")
        sku_dir = os.path.join(self.temp_dir, "sku")
        os.makedirs(gal_dir)
        os.makedirs(sku_dir)

        # Create dummy test images
        img_paths = [
            os.path.join(gal_dir, "gallery_01.jpg"),
            os.path.join(sku_dir, "RN8-SIL-WT-S.jpg")
        ]
        for p in img_paths:
            img = Image.new("RGB", (800, 800), color=(240, 240, 240))
            img.save(p, "JPEG", quality=95)

        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = urllib.error.URLError("Network unreachable")

            results = self.translator.translate_directory(
                self.temp_dir,
                model_name="Realme Neo8",
                material="Liquid Silicone",
                dry_run=False
            )
            self.assertEqual(len(results), 2)
            for p in img_paths:
                self.assertTrue(os.path.exists(p))
                with Image.open(p) as res_img:
                    self.assertEqual(res_img.size, (800, 800))
                    self.assertEqual(res_img.mode, "RGB")


class TestGitSyncAdversarial(unittest.TestCase):
    """Stress tests git auto-sync rebase conflicts, detached HEAD, and concurrency."""

    def setUp(self):
        self.temp_repo = tempfile.mkdtemp(prefix="adv_git_")
        # Initialize an isolated Git repository
        subprocess.run(["git", "init"], cwd=self.temp_repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.temp_repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_repo, check=True)

        # Initial commit
        readme = os.path.join(self.temp_repo, "README.md")
        with open(readme, "w") as f:
            f.write("# CoverStore Test Repo\n")
        subprocess.run(["git", "add", "."], cwd=self.temp_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.temp_repo, check=True)

    def tearDown(self):
        if os.path.exists(self.temp_repo):
            shutil.rmtree(self.temp_repo, ignore_errors=True)

    def test_rebase_conflict_auto_aborts_safely(self):
        """
        Adversarial rebase conflict test:
        Simulates a git pull --rebase failure that generates a merge conflict.
        Verifies that auto_sync detects the conflict and invokes git rebase --abort,
        leaving working tree in a clean state rather than hanging in rebasing state.
        """
        # Create a conflicting branch
        subprocess.run(["git", "branch", "feature"], cwd=self.temp_repo, check=True)

        # Modify on main
        readme = os.path.join(self.temp_repo, "README.md")
        with open(readme, "w") as f:
            f.write("# Main Branch Change\nLine from main\n")
        subprocess.run(["git", "commit", "-am", "Change on main"], cwd=self.temp_repo, check=True)

        # Modify on feature with direct conflict
        subprocess.run(["git", "checkout", "feature"], cwd=self.temp_repo, check=True)
        with open(readme, "w") as f:
            f.write("# Feature Branch Change\nLine from feature\n")
        subprocess.run(["git", "commit", "-am", "Change on feature"], cwd=self.temp_repo, check=True)

        # Attempt pull/rebase with auto_sync logic targeting main
        # We invoke perform_sync with remote='.' and branch='main'
        sync_result = perform_sync(branch="main", remote=".")
        self.assertFalse(sync_result)

        # Check repository state: rebase MUST be aborted, not in progress!
        rebase_merge = os.path.join(self.temp_repo, ".git", "rebase-merge")
        rebase_apply = os.path.join(self.temp_repo, ".git", "rebase-apply")
        self.assertFalse(os.path.exists(rebase_merge), "Rebase merge directory still exists!")
        self.assertFalse(os.path.exists(rebase_apply), "Rebase apply directory still exists!")

    def test_detached_head_handling(self):
        """
        Adversarial git test:
        Verifies behavior when repository is in detached HEAD state.
        """
        # Detach HEAD to initial commit
        proc = subprocess.run(["git", "rev-parse", "HEAD~0"], cwd=self.temp_repo, capture_output=True, text=True, check=True)
        commit_hash = proc.stdout.strip()
        subprocess.run(["git", "checkout", commit_hash], cwd=self.temp_repo, capture_output=True, check=True)

        # Verify detached HEAD
        branch_proc = subprocess.run(["git", "branch", "--show-current"], cwd=self.temp_repo, capture_output=True, text=True, check=True)
        self.assertEqual(branch_proc.stdout.strip(), "")

        # Test git_commit_and_push from pipeline_orchestrator
        with patch("pipeline_orchestrator.get_git_binary", return_value="git"):
            # Add a file
            test_file = os.path.join(self.temp_repo, "test.txt")
            with open(test_file, "w") as f:
                f.write("detached head test\n")

            # git_commit_and_push will stage, commit, and attempt push
            # Push will fail safely (or rebase/push will return False) without raising unhandled Python exceptions
            success = git_commit_and_push("test commit", cwd=self.temp_repo)
            self.assertIsInstance(success, bool)

    def test_pipeline_orchestrator_non_interactive_rule_9_rejection(self):
        """
        Adversarial Rule 9 test:
        Confirms pipeline_orchestrator immediately raises ValueError when
        --china-delivery is omitted and stdin is non-interactive.
        """
        orch = PipelineOrchestrator(
            url="https://moveon.global/test-url",
            china_delivery=None,
            dry_run=True
        )
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(ValueError) as ctx:
                orch.run_agent1()
            self.assertIn("Mandatory China domestic delivery charge (Rule 9) is required", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
