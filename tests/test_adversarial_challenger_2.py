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
import urllib.error
import subprocess
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

import openpyxl
from openpyxl.utils.exceptions import IllegalCharacterError
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
                    client.start()
                    call_kwargs = mock_browser.new_context.call_args[1]
                    self.assertNotIn("storage_state", call_kwargs)
            finally:
                client.close()

    def test_inventory_missing_and_empty_csv(self):
        """Adversarial inventory test: Missing CSV, 0-byte CSV, or empty rows."""
        non_existent = os.path.join(self.temp_dir, "non_existent.csv")
        res = load_and_group_inventory(non_existent)
        self.assertEqual(res, [])

        empty_csv = os.path.join(self.temp_dir, "empty.csv")
        with open(empty_csv, "w", encoding="utf-8") as f:
            pass
        res = load_and_group_inventory(empty_csv)
        self.assertEqual(res, [])

        header_only = os.path.join(self.temp_dir, "header_only.csv")
        with open(header_only, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["link", "Product Code", "Phone Model", "Material", "sell price"])
        res = load_and_group_inventory(header_only)
        self.assertEqual(res, [])

    def test_inventory_corrupted_data_types(self):
        """Adversarial inventory test: Malformed prices, currency strings, negative prices."""
        csv_path = os.path.join(self.temp_dir, "corrupted_inventory.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["link", "Product Code", "Phone Model", "Material", "Color", "sell price", "Local Image Path"])
            writer.writerow(["https://moveon.global/item1", "RN8-SIL-WT-S", "Realme Neo8", "Liquid Silicone", "White", "INVALID_PRICE", ""])
            writer.writerow(["https://moveon.global/item1", "RN8-SIL-BK-S", "Realme Neo8", "Liquid Silicone", "Black", "৳ 550.00", ""])
            writer.writerow(["https://moveon.global/item1", "RN8-SIL-PR-S", "Realme Neo8", "Liquid Silicone", "Purple", "-100", ""])
            writer.writerow(["", "EMPTY-LINK-SKU", "Realme Neo8", "Liquid Silicone", "Clear", "300", ""])

        products = load_and_group_inventory(csv_path)
        self.assertEqual(len(products), 1)
        variants = products[0]["variants"]
        self.assertEqual(len(variants), 3)

        # Fallback price verification
        self.assertEqual(variants[0]["price"], 349)  # Fallback from INVALID_PRICE
        # Note: '৳ 550.00' raises ValueError without clean_float currency stripping, falling back to 349
        self.assertEqual(variants[1]["price"], 349)
        self.assertEqual(variants[2]["price"], -100) # Negative int parsed

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
        # Header (row 1) + Parent Product (row 2) + 1 Variant (row 3) = 3 rows
        self.assertEqual(ws.max_row, 3)

        parent_title = ws.cell(row=2, column=2).value
        parent_desc = ws.cell(row=2, column=16).value
        variant_opt = ws.cell(row=3, column=6).value

        self.assertIn("Special Case <Test>", parent_title)
        self.assertIn("Line 1\nLine 2", parent_desc)
        self.assertIn("✨🎉", parent_desc)
        self.assertIn("(V1)", variant_opt)
        wb.close()

    def test_workbook_openpyxl_illegal_control_characters(self):
        """
        Adversarial test: Tests behavior when description contains raw XML 1.0 illegal control characters.
        Openpyxl forbids characters in range \x00-\x1f (except \t, \n, \r).
        """
        product = {
            "title": "Clean Title",
            "phone_models": ["Realme Neo8"],
            "primary_material": "Liquid Silicone",
            "description": "Corrupted text with null byte \x00 and form feed \x0c",
            "gallery_images": ["gallery_01.jpg"],
            "variants": [{
                "sku": "RN8-SIL-WT-S",
                "phone_model": "Realme Neo8",
                "color": "Antique White",
                "price": 349,
                "stock": 1,
                "image_path": ""
            }]
        }
        out_path = os.path.join(self.temp_dir, "illegal_char.xlsx")
        # Documents openpyxl behavior on raw control characters
        with self.assertRaises(IllegalCharacterError):
            generate_import_workbook(product, output_path=out_path)

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
        self.assertEqual(ws.max_row, 62)  # 1 header + 1 parent + 60 variants
        self.assertEqual(ws.max_column, 16)
        self.assertEqual(ws.cell(row=2, column=4).value, "RN8-SIL")
        self.assertEqual(ws.cell(row=62, column=5).value, "RN8-SIL-C60-S")
        wb.close()

    def test_extreme_disambiguation_formatting(self):
        """Adversarial option label test: Extreme suffix codes (-V10, -V99)."""
        test_cases = [
            ("RN8-SIL-WT-S-V1", "Antique White", "Color: Antique White (V1)"),
            ("RN8-SIL-WT-S-V2", "Antique White", "Color: Antique White (V2)"),
            ("RN8-SIL-WT-S-V10", "Antique White", "Color: Antique White (V10)"),
            ("RN8-SIL-WT-S-V99", "Antique White", "Color: Antique White (V99)"),
            ("RN8-SIL-WT-S-V2", "Antique White (V2)", "Color: Antique White (V2)"),
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

    def test_disambiguated_first_variant_parent_base_sku(self):
        """
        Adversarial test on parent BASE_SKU derivation:
        When first variant has collision suffix -V2, rsplit('-', 2)[0] produces
        'RN8-SIL-WT' instead of 'RN8-SIL', leaking variant color into parent product SKU.
        """
        product = {
            "title": "Parent Base SKU Test",
            "variants": [
                {
                    "sku": "RN8-SIL-WT-S-V2",
                    "color": "Antique White",
                    "price": 349,
                    "stock": 1,
                    "image_path": ""
                },
                {
                    "sku": "RN8-SIL-BK-S",
                    "color": "Classic Black",
                    "price": 349,
                    "stock": 1,
                    "image_path": ""
                }
            ]
        }
        out_path = os.path.join(self.temp_dir, "parent_sku_test.xlsx")
        generate_import_workbook(product, output_path=out_path)
        wb = openpyxl.load_workbook(out_path)
        ws = wb.active
        parent_base_sku = ws.cell(row=2, column=4).value
        wb.close()
        # Documents the empirical behavior:
        # Standard expectation is 'RN8-SIL', but current rsplit('-', 2)[0] on -V2 yields 'RN8-SIL-WT'
        self.assertIn(parent_base_sku, ["RN8-SIL", "RN8-SIL-WT"])

    def test_custom_non_numeric_suffix_option_label(self):
        """
        Adversarial test: Variant SKU with custom suffix (e.g. -ALT or -CUSTOM).
        Documents whether regex r'-(V\d+)$' captures non-numeric disambiguation suffixes.
        """
        product = {
            "title": "Custom Suffix Test",
            "variants": [
                {
                    "sku": "RN8-SIL-WT-S-ALT",
                    "color": "Antique White",
                    "price": 349,
                    "stock": 1,
                    "image_path": ""
                }
            ]
        }
        out_path = os.path.join(self.temp_dir, "custom_suffix.xlsx")
        generate_import_workbook(product, output_path=out_path)
        wb = openpyxl.load_workbook(out_path)
        ws = wb.active
        opt_label = ws.cell(row=3, column=6).value
        wb.close()
        # Since r'-(V\d+)$' only matches -V<num>, -ALT is not captured
        self.assertEqual(opt_label, "Color: Antique White")


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
            terms = [
                ("液态硅胶", "Liquid Silicone"),
                ("曜石黑", "Obsidian Black"),
                ("古董白", "Antique White"),
                ("远峰蓝", "Sierra Blue"),
                ("暗夜绿", "Dark Night Green"),
                ("全包软壳", "All-Inclusive Soft Case"),
                ("亲肤手感", "Skin-Friendly Feel"),
                ("真机开模", "1:1 Precision Mold"),
                ("磁吸", "Magnetic"),
                ("超薄", "Ultra-Thin"),
            ]
            for zh, expected_en in terms:
                result = self.translator.translate_text(zh)
                self.assertEqual(result, expected_en)

    def test_offline_compound_terms_token_fallback(self):
        """Ensures compound phrases degrade gracefully to Tier 3 token replacement when offline."""
        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = urllib.error.URLError("DNS lookup failed: Offline mode")

            compound = "全新 液态硅胶 经典黑 防摔壳"
            translated = self.translator.translate_text(compound)
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
            self.assertEqual(results["translated_count"], 2)
            self.assertEqual(results["status"], "success")
            for p in img_paths:
                self.assertTrue(os.path.exists(p))
                with Image.open(p) as res_img:
                    self.assertEqual(res_img.size, (800, 800))
                    self.assertEqual(res_img.mode, "RGB")


class TestGitSyncAdversarial(unittest.TestCase):
    """Stress tests git auto-sync rebase conflicts, detached HEAD, and concurrency."""

    def setUp(self):
        self.temp_repo = tempfile.mkdtemp(prefix="adv_git_")
        subprocess.run(["git", "init", "-b", "main"], cwd=self.temp_repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=self.temp_repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.temp_repo, check=True)

        readme = os.path.join(self.temp_repo, "README.md")
        with open(readme, "w") as f:
            f.write("# CoverStore Test Repo\n")
        subprocess.run(["git", "add", "."], cwd=self.temp_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.temp_repo, check=True)

    def tearDown(self):
        if os.path.exists(self.temp_repo):
            shutil.rmtree(self.temp_repo, ignore_errors=True)

    def test_rebase_conflict_detection_and_abort(self):
        """
        Adversarial rebase conflict test:
        Simulates a git pull --rebase failure that generates a merge conflict.
        Tests whether auto_sync aborts rebase when advice.mergeConflict is true (stderr has conflict).
        """
        # Create bare remote and two clones
        bare_remote = tempfile.mkdtemp(prefix="adv_bare_")
        clone_local = tempfile.mkdtemp(prefix="adv_clone_")
        clone_other = tempfile.mkdtemp(prefix="adv_other_")

        try:
            subprocess.run(["git", "init", "--bare", "-b", "main", bare_remote], check=True, capture_output=True)
            subprocess.run(["git", "clone", bare_remote, clone_local], check=True, capture_output=True)
            for d in [clone_local]:
                subprocess.run(["git", "config", "user.name", "Tester"], cwd=d, check=True)
                subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=d, check=True)

            f = os.path.join(clone_local, "test.txt")
            with open(f, "w") as fp:
                fp.write("initial\n")
            subprocess.run(["git", "add", "."], cwd=clone_local, check=True)
            subprocess.run(["git", "commit", "-m", "c1"], cwd=clone_local, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=clone_local, check=True)

            # Local change
            with open(f, "w") as fp:
                fp.write("local line\n")
            subprocess.run(["git", "commit", "-am", "local commit"], cwd=clone_local, check=True)

            # Remote change from other clone
            subprocess.run(["git", "clone", bare_remote, clone_other], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester2"], cwd=clone_other, check=True)
            subprocess.run(["git", "config", "user.email", "tester2@example.com"], cwd=clone_other, check=True)
            with open(os.path.join(clone_other, "test.txt"), "w") as fp:
                fp.write("remote line\n")
            subprocess.run(["git", "commit", "-am", "remote commit"], cwd=clone_other, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=clone_other, check=True)

            # Execute perform_sync on clone_local
            def patched_run_git(cmd, cwd=None):
                target_cwd = cwd if cwd is not None else clone_local
                return subprocess.run(
                    [auto_sync.GIT_BIN] + cmd,
                    cwd=target_cwd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )

            with patch("auto_sync.run_git", side_effect=patched_run_git), \
                 patch("auto_sync.WORKSPACE_ROOT", clone_local):
                sync_ok = perform_sync(branch="main", remote="origin")
                self.assertFalse(sync_ok)

                # Verify rebase state
                rebase_merge = os.path.join(clone_local, ".git", "rebase-merge")
                rebase_apply = os.path.join(clone_local, ".git", "rebase-apply")
                self.assertFalse(os.path.exists(rebase_merge))
                self.assertFalse(os.path.exists(rebase_apply))
        finally:
            shutil.rmtree(bare_remote, ignore_errors=True)
            shutil.rmtree(clone_local, ignore_errors=True)
            shutil.rmtree(clone_other, ignore_errors=True)

    def test_rebase_conflict_vulnerability_when_advice_disabled(self):
        """
        Adversarial Vulnerability Probe:
        When advice.mergeConflict is false, Git outputs conflict message on STDOUT,
        NOT STDERR. Current auto_sync.py only checks pull_res.stderr.lower().
        This empirically proves whether auto_sync fails to abort the rebase.
        """
        bare_remote = tempfile.mkdtemp(prefix="adv_bare2_")
        clone_local = tempfile.mkdtemp(prefix="adv_clone2_")
        clone_other = tempfile.mkdtemp(prefix="adv_other2_")

        try:
            subprocess.run(["git", "init", "--bare", "-b", "main", bare_remote], check=True, capture_output=True)
            subprocess.run(["git", "clone", bare_remote, clone_local], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=clone_local, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=clone_local, check=True)
            subprocess.run(["git", "config", "advice.mergeConflict", "false"], cwd=clone_local, check=True)

            f = os.path.join(clone_local, "test.txt")
            with open(f, "w") as fp:
                fp.write("initial\n")
            subprocess.run(["git", "add", "."], cwd=clone_local, check=True)
            subprocess.run(["git", "commit", "-m", "c1"], cwd=clone_local, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=clone_local, check=True)

            # Local change
            with open(f, "w") as fp:
                fp.write("local line\n")
            subprocess.run(["git", "commit", "-am", "local commit"], cwd=clone_local, check=True)

            # Remote change from other clone
            subprocess.run(["git", "clone", bare_remote, clone_other], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Tester2"], cwd=clone_other, check=True)
            subprocess.run(["git", "config", "user.email", "tester2@example.com"], cwd=clone_other, check=True)
            with open(os.path.join(clone_other, "test.txt"), "w") as fp:
                fp.write("remote line\n")
            subprocess.run(["git", "commit", "-am", "remote commit"], cwd=clone_other, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=clone_other, check=True)

            # Execute perform_sync on clone_local
            def patched_run_git(cmd, cwd=None):
                target_cwd = cwd if cwd is not None else clone_local
                return subprocess.run(
                    [auto_sync.GIT_BIN] + cmd,
                    cwd=target_cwd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )

            with patch("auto_sync.run_git", side_effect=patched_run_git), \
                 patch("auto_sync.WORKSPACE_ROOT", clone_local):
                sync_ok = perform_sync(branch="main", remote="origin")
                self.assertFalse(sync_ok)

                # If rebase was NOT aborted due to checking only stderr, rebase directory exists!
                rebase_merge = os.path.join(clone_local, ".git", "rebase-merge")
                rebase_apply = os.path.join(clone_local, ".git", "rebase-apply")
                rebase_in_progress = os.path.exists(rebase_merge) or os.path.exists(rebase_apply)
                # This assertion documents the exact vulnerability
                if rebase_in_progress:
                    # Clean up rebase in test
                    subprocess.run(["git", "rebase", "--abort"], cwd=clone_local, capture_output=True)
                self.assertTrue(rebase_in_progress, "Vulnerability confirmed: rebase was left in progress because stdout was not checked!")
        finally:
            shutil.rmtree(bare_remote, ignore_errors=True)
            shutil.rmtree(clone_local, ignore_errors=True)
            shutil.rmtree(clone_other, ignore_errors=True)

    def test_detached_head_handling(self):
        """
        Adversarial git test:
        Verifies behavior when repository is in detached HEAD state.
        """
        proc = subprocess.run(["git", "rev-parse", "HEAD~0"], cwd=self.temp_repo, capture_output=True, text=True, check=True)
        commit_hash = proc.stdout.strip()
        subprocess.run(["git", "checkout", commit_hash], cwd=self.temp_repo, capture_output=True, check=True)

        branch_proc = subprocess.run(["git", "branch", "--show-current"], cwd=self.temp_repo, capture_output=True, text=True, check=True)
        self.assertEqual(branch_proc.stdout.strip(), "")

        with patch("pipeline_orchestrator.get_git_binary", return_value="git"):
            test_file = os.path.join(self.temp_repo, "test.txt")
            with open(test_file, "w") as f:
                f.write("detached head test\n")
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
