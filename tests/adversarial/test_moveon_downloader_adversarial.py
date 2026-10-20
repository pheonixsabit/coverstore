import unittest
import sys
import os
import io
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from moveon_client import (
    extract_product_id_from_url,
    clean_model_name,
    sanitize_filename,
    MoveOnClient
)
from inventory_manager import prompt_china_delivery

class TestMoveOnDownloaderAdversarial(unittest.TestCase):
    """Adversarial stress testing for MoveOn client and downloader routines."""

    def test_extract_product_id_empty_and_whitespace(self):
        """Stress test with empty, whitespace, and nonsense URLs."""
        self.assertEqual(extract_product_id_from_url(""), "")
        self.assertEqual(extract_product_id_from_url("   "), "")
        self.assertEqual(extract_product_id_from_url("\t\r\n"), "")

    def test_extract_product_id_malformed_urls(self):
        """Test URLs with missing segments or broken structure."""
        # Missing part 2
        res1 = extract_product_id_from_url("https://moveon.global/BD_en/products/0000000MJPDSKGCI-slug")
        # Should fallback to alphanumeric extraction or clean ID
        self.assertNotIn("/", res1)

        # Raw composite ID directly passed
        res2 = extract_product_id_from_url("1AD83545744841150000000MJPDSKGCI")
        self.assertEqual(res2, "1AD83545744841150000000MJPDSKGCI")

        # URL with query params & hash fragment
        url_with_query = "https://moveon.global/BD_en/products/0000000MJPDSKGCI-slug/1AD8354574484115?ref=tracker&utm=123#spec"
        self.assertEqual(extract_product_id_from_url(url_with_query), "1AD83545744841150000000MJPDSKGCI")

        # Path traversal and injection strings
        injected = "https://moveon.global/BD_en/products/..%2F..%2Fetc/passwd"
        res_inj = extract_product_id_from_url(injected)
        self.assertNotIn("..", res_inj)
        self.assertNotIn("/", res_inj)

    def test_extract_product_id_extreme_payloads(self):
        """Stress test with huge 100k character string and unicode/emoji."""
        huge_url = "https://moveon.global/BD_en/products/" + ("A" * 50000) + "-slug/" + ("B" * 50000)
        res = extract_product_id_from_url(huge_url)
        self.assertEqual(len(res), 100000)
        self.assertTrue(res.startswith("B"))

        emoji_url = "https://moveon.global/BD_en/products/📱-phone/🔥123"
        res_emoji = extract_product_id_from_url(emoji_url)
        self.assertIsInstance(res_emoji, str)

    def test_clean_model_name_adversarial(self):
        """Stress test phone model cleaning with illegal characters, unicode, and nested brackets."""
        # Windows illegal characters
        illegal_str = 'Realme <Neo:8>*?"|/\\'
        cleaned = clean_model_name(illegal_str)
        for char in '<>:*?"|/\\':
            self.assertNotIn(char, cleaned)

        # Chinese brackets and nested spec phrases
        messy_name = "【1 case】suitable for realme neo 8 【hot sale】 (1 case)"
        cleaned_m = clean_model_name(messy_name)
        self.assertNotIn("【", cleaned_m)
        self.assertNotIn("】", cleaned_m)
        self.assertNotIn("1 case", cleaned_m)
        self.assertTrue("Realme" in cleaned_m or "Neo8" in cleaned_m)

        # Empty / whitespace
        self.assertEqual(clean_model_name(""), "")
        self.assertEqual(clean_model_name("   "), "")

        # Unicode RTL override characters
        rtl_str = "\u202eRealme Neo8\u202c"
        cleaned_rtl = clean_model_name(rtl_str)
        self.assertIsInstance(cleaned_rtl, str)

    def test_sanitize_filename_adversarial(self):
        """Stress test sanitize_filename against traversal and illegal chars."""
        self.assertEqual(sanitize_filename("a/b\\c:d*e?f\"g<h>i|j"), "a_b_c_d_e_f_g_h_i_j")
        self.assertEqual(sanitize_filename("   multiple    spaces   "), "multiple spaces")
        self.assertEqual(sanitize_filename(""), "")

    def test_moveon_client_corrupted_api_responses(self):
        """Simulate adversarial API responses from MoveOn: corrupted JSON, missing keys, empty dictionaries."""
        client = MoveOnClient(auth_token="dummy_token")

        # 1. Non-existent product ID
        with self.assertRaises(ValueError):
            client.fetch_product("    ")

        # 2. Corrupted JSON returned by server
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = b"<html>502 Bad Gateway</html>"
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with self.assertRaises(RuntimeError) as ctx:
                client.fetch_product("https://moveon.global/BD_en/products/PART1-slug/PART2")
            self.assertIn("Network error communicating with MoveOn API", str(ctx.exception))

        # 3. Empty data dictionary
        mock_resp.read.return_value = json.dumps({"data": {}}).encode("utf-8")
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with self.assertRaises(ValueError) as ctx:
                client.fetch_product("https://moveon.global/BD_en/products/PART1-slug/PART2")
            self.assertIn("No product data returned", str(ctx.exception))

        # 4. Variation dictionary completely missing
        payload_no_var = {
            "data": {
                "title": "Minimal Case",
                "image": "https://img.example.com/main.jpg",
                "gallery": {"data": []}
            }
        }
        mock_resp.read.return_value = json.dumps(payload_no_var).encode("utf-8")
        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = client.fetch_product("https://moveon.global/BD_en/products/PART1-slug/PART2")
            self.assertEqual(res["title"], "Minimal Case")
            self.assertEqual(len(res["models"]), 0)
            self.assertEqual(res["gallery_images"], ["https://img.example.com/main.jpg"])

        # 5. Variation present but SKUs missing property associations
        payload_orphan_skus = {
            "data": {
                "title": "Case with Orphan SKUs",
                "gallery": {"data": [{"url": "https://img.example.com/1.jpg"}]},
                "variation": {
                    "properties": {"data": []},
                    "skus": {
                        "data": [
                            {"id": 101, "price": {"original": 40.0}},
                            {"id": 102, "price": {"original": 45.0}}
                        ]
                    }
                }
            }
        }
        mock_resp.read.return_value = json.dumps(payload_orphan_skus).encode("utf-8")
        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = client.fetch_product("https://moveon.global/BD_en/products/PART1-slug/PART2")
            self.assertIn("Standard Model", res["skus_by_model"])
            self.assertEqual(len(res["skus_by_model"]["Standard Model"]), 2)

    def test_china_delivery_prompt_adversarial_enforcement(self):
        """Stress test Rule 9 mandatory China domestic delivery charge enforcement."""
        # Non-interactive without value MUST raise ValueError
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(ValueError) as ctx:
                prompt_china_delivery(None)
            self.assertIn("Rule 9", str(ctx.exception))

        # Negative value MUST raise ValueError
        with self.assertRaises(ValueError):
            prompt_china_delivery(-5.0)

        # Zero is valid
        self.assertEqual(prompt_china_delivery(0.0), 0.0)

        # String with symbols converted cleanly
        self.assertEqual(prompt_china_delivery("15.50"), 15.50)


if __name__ == "__main__":
    unittest.main()
