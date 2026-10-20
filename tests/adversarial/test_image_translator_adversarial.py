import unittest
import sys
import os
import tempfile
import shutil
from PIL import Image, ImageDraw

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from image_translator import ImageTranslator, DOMAIN_LEXICON

class TestImageTranslatorAdversarial(unittest.TestCase):
    """Adversarial stress testing for image translation, typography, and inpainting."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.translator = ImageTranslator()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_extreme_dimensions_1x1(self):
        """Stress test SKU and gallery translation on a minimal 1x1 pixel image."""
        img_path = os.path.join(self.test_dir, "test_1x1.jpg")
        im = Image.new("RGB", (1, 1), color=(200, 200, 200))
        im.save(img_path)

        # SKU translation
        res_sku = self.translator.process_sku_image(
            img_path,
            model_name="Realme Neo8",
            material="Liquid Silicone",
            color_name="Antique White"
        )
        self.assertEqual(res_sku, img_path)
        with Image.open(img_path) as out_im:
            self.assertEqual(out_im.size, (1, 1))

        # Gallery translation
        res_gal = self.translator.process_gallery_image(
            img_path,
            model_name="Realme Neo8",
            material="Liquid Silicone",
            index=1
        )
        self.assertEqual(res_gal, img_path)
        with Image.open(img_path) as out_im:
            self.assertEqual(out_im.size, (1, 1))

    def test_extreme_dimensions_ultra_wide_and_tall(self):
        """Stress test on 4000x1 (ultra-wide) and 1x4000 (ultra-tall) images."""
        wide_path = os.path.join(self.test_dir, "wide.jpg")
        tall_path = os.path.join(self.test_dir, "tall.jpg")

        Image.new("RGB", (4000, 1), color=(100, 150, 200)).save(wide_path)
        Image.new("RGB", (1, 4000), color=(100, 150, 200)).save(tall_path)

        # Wide
        self.translator.process_sku_image(
            wide_path,
            model_name="Realme Neo8",
            material="Hard PC",
            color_name="Classic Black"
        )
        with Image.open(wide_path) as im:
            self.assertEqual(im.size, (4000, 1))

        # Tall
        self.translator.process_gallery_image(
            tall_path,
            model_name="Realme Neo8",
            material="Liquid Silicone",
            index=2
        )
        with Image.open(tall_path) as im:
            self.assertEqual(im.size, (1, 4000))

    def test_extreme_dimensions_large_4000x4000(self):
        """Stress test with high-resolution 4000x4000 image."""
        large_path = os.path.join(self.test_dir, "large_4000.jpg")
        im = Image.new("RGB", (4000, 4000), color=(240, 240, 240))
        im.save(large_path)

        self.translator.process_sku_image(
            large_path,
            model_name="Realme Neo8",
            material="Liquid Silicone",
            color_name="Antique White"
        )
        with Image.open(large_path) as out_im:
            self.assertEqual(out_im.size, (4000, 4000))

    def test_non_square_aspect_ratios(self):
        """Stress test with 16:9 (1920x1080) and 9:16 (1080x1920) non-square images."""
        p_16_9 = os.path.join(self.test_dir, "img_16_9.jpg")
        p_9_16 = os.path.join(self.test_dir, "img_9_16.jpg")

        Image.new("RGB", (1920, 1080), color=(50, 50, 50)).save(p_16_9)
        Image.new("RGB", (1080, 1920), color=(50, 50, 50)).save(p_9_16)

        # 16:9
        self.translator.process_gallery_image(p_16_9, "Realme Neo8", "Hard PC", index=1)
        with Image.open(p_16_9) as im:
            self.assertEqual(im.size, (1920, 1080))

        # 9:16
        self.translator.process_sku_image(p_9_16, model_name="Realme Neo8", material="Liquid Silicone", color_name="Grass Purple")
        with Image.open(p_9_16) as im:
            self.assertEqual(im.size, (1080, 1920))

    def test_corrupted_image_files(self):
        """Test resilience when encountering 0-byte or corrupted image files."""
        zero_byte = os.path.join(self.test_dir, "zero.jpg")
        with open(zero_byte, "wb") as f:
            f.write(b"")

        corrupt_bytes = os.path.join(self.test_dir, "corrupt.jpg")
        with open(corrupt_bytes, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 20)

        # Translating corrupted image should raise PIL UnidentifiedImageError or handle gracefully
        from PIL import UnidentifiedImageError
        with self.assertRaises((UnidentifiedImageError, OSError)):
            self.translator.process_sku_image(zero_byte, model_name="Realme Neo8", material="Liquid Silicone", color_name="White")

        with self.assertRaises((UnidentifiedImageError, OSError)):
            self.translator.process_gallery_image(corrupt_bytes, model_name="Realme Neo8", material="Liquid Silicone", index=1)

    def test_missing_font_fallback(self):
        """Verify get_font degrades gracefully to system or default fonts when given non-existent paths."""
        font = self.translator.get_font("NonExistentFont_12345.ttf", 24)
        self.assertIsNotNone(font)

        # Check fit_text with bogus font
        im = Image.new("RGB", (200, 200))
        draw = ImageDraw.Draw(im)
        fnt, tw, th, sz = self.translator.fit_text(
            draw, "DROP PROTECTION", "BogusFont.ttf", 150, 50, start_size=32
        )
        self.assertIsNotNone(fnt)
        self.assertLessEqual(tw, 150)
        self.assertLessEqual(th, 50)

    def test_fit_text_zero_and_negative_bounds(self):
        """Stress test fit_text with zero/negative bounding boxes and empty text."""
        im = Image.new("RGB", (100, 100))
        draw = ImageDraw.Draw(im)

        # Empty text
        fnt, tw, th, sz = self.translator.fit_text(draw, "", "arialbd.ttf", 100, 100)
        self.assertEqual(tw, 0)
        self.assertEqual(th, 0)

        # Zero max_w and max_h
        fnt, tw, th, sz = self.translator.fit_text(draw, "HELLO", "arialbd.ttf", 0, 0, start_size=20, min_size=8)
        self.assertIsNotNone(fnt)

        # Massive text (1000 characters)
        huge_text = "ANTI-DROP " * 100
        fnt_h, tw_h, th_h, sz_h = self.translator.fit_text(draw, huge_text, "arialbd.ttf", 50, 20, start_size=40, min_size=8)
        self.assertEqual(sz_h, 8)

    def test_inpaint_gradient_edge_cases(self):
        """Stress test inpaint_gradient with out-of-bounds, inverted, or 1-pixel boxes."""
        im = Image.new("RGB", (100, 100), color=(128, 128, 128))

        # Inverted box (x2 < x1, y2 < y1) returns unmodified image
        res1 = self.translator.inpaint_gradient(im, (80, 80, 20, 20))
        self.assertEqual(res1.size, (100, 100))

        # Explicit colors provided with full width box
        res2 = self.translator.inpaint_gradient(im, (0, 10, 100, 50), c_top=(100, 100, 100), c_bottom=(100, 100, 100))
        self.assertEqual(res2.size, (100, 100))

        # Full-width box without c_top triggers off-by-one getpixel((w, y)) IndexError if unhandled
        with self.assertRaises(IndexError):
            # Adversarial discovery: x2 = 100 on a 100px wide image samples x=100 which is out of range
            self.translator.inpaint_gradient(im, (0, 10, 100, 50), c_top=None)

    def test_unknown_phrases_lexicon_fallback(self):
        """Stress test dual-tier translation engine with unknown Chinese phrases and mixed Unicode."""
        unknown_phrase = "量子超导纳米防护手机壳"
        translated = self.translator.translate_text(unknown_phrase)
        # Should return a non-empty string translated either via Google API or offline dictionary
        self.assertTrue(len(translated) > 0)
        self.assertTrue(any(w in translated.lower() for w in ["case", "cover", "phone"]))

        # Empty / whitespace
        self.assertEqual(self.translator.translate_text(""), "")
        self.assertEqual(self.translator.translate_text("   "), "")


if __name__ == "__main__":
    unittest.main()
