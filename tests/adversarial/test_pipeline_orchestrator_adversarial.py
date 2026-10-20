import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from PIL import Image

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from pipeline_orchestrator import PipelineOrchestrator

class TestPipelineOrchestratorAdversarial(unittest.TestCase):
    """Adversarial stress testing for unified pipeline orchestrator."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_missing_url_raises_error(self):
        """Stress test orchestrator instantiation and Agent 1 run with missing/empty URL."""
        orch = PipelineOrchestrator(url="")
        with self.assertRaises(ValueError) as ctx:
            orch.run_agent1()
        self.assertIn("URL", str(ctx.exception))

    def test_omitted_china_delivery_non_interactive_halt(self):
        """Verify orchestrator strictly enforces Rule 9 when running non-interactively without --china-delivery."""
        orch = PipelineOrchestrator(
            url="https://moveon.global/BD_en/products/0000000MJPDSKGCI-slug/1AD8354574484115",
            china_delivery=None
        )
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(ValueError) as ctx:
                orch.run_agent1()
            self.assertIn("Rule 9", str(ctx.exception))

    def test_agent1_failure_aborts_pipeline(self):
        """Verify failure in Agent 1 halts execution immediately and raises RuntimeError."""
        orch = PipelineOrchestrator(
            url="https://moveon.global/BD_en/products/0000000MJPDSKGCI-slug/1AD8354574484115",
            china_delivery=10.0,
            dry_run=False
        )
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        with patch("subprocess.run", return_value=mock_proc):
            with self.assertRaises(RuntimeError) as ctx:
                orch.run_agent1()
            self.assertIn("downloader.py", str(ctx.exception))

    def test_agent2_validation_detects_corrupted_output(self):
        """Verify Agent 2 handoff validation catches empty or unreadable images."""
        gal_dir = os.path.join(self.test_dir, "gallery")
        sku_dir = os.path.join(self.test_dir, "sku")
        os.makedirs(gal_dir, exist_ok=True)
        os.makedirs(sku_dir, exist_ok=True)

        # Create valid image in gallery
        Image.new("RGB", (100, 100)).save(os.path.join(gal_dir, "gallery_01.jpg"))

        # Create 0-byte corrupt image in sku
        corrupt_path = os.path.join(sku_dir, "RN8-SIL-WT-S.jpg")
        with open(corrupt_path, "wb") as f:
            f.write(b"")

        orch = PipelineOrchestrator(
            url="https://moveon.global/test",
            china_delivery=10.0,
            dry_run=False
        )
        handoff_a1 = {
            "model": "Realme Neo8",
            "material": "Liquid Silicone",
            "target_dir": self.test_dir,
            "url": "https://moveon.global/test"
        }

        with patch("image_translator.ImageTranslator.translate_directory", return_value={}):
            with self.assertRaises(Exception):
                orch.run_agent2(handoff_a1)

    def test_agent3_skip_pathao_flag(self):
        """Verify --skip-pathao cleanly bypasses marketplace synchronization."""
        orch = PipelineOrchestrator(
            url="https://moveon.global/test",
            china_delivery=10.0,
            skip_pathao=True
        )
        res = orch.run_agent3({})
        self.assertEqual(res.get("status"), "skipped")
        self.assertIsNone(res.get("product_id"))

    def test_verification_failure_blocks_git_sync(self):
        """Verify failed E2E tests halt the orchestrator and block git commit/push."""
        orch = PipelineOrchestrator(
            url="https://moveon.global/test",
            china_delivery=10.0,
            dry_run=False
        )
        mock_test_proc = MagicMock()
        mock_test_proc.returncode = 1
        mock_test_proc.stdout = "FAILED (errors=1)"
        mock_test_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_test_proc):
            with self.assertRaises(RuntimeError) as ctx:
                orch.run_verification()
            self.assertIn("Pipeline verification test suite failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
