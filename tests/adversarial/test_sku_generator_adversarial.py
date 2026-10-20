import unittest
import sys
import os
import re

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from sku_generator import (
    generate_sku,
    disambiguate_sku,
    resolve_sku_collision,
    abbreviate_model,
    abbreviate_material,
    abbreviate_color,
    abbreviate_print,
    register_custom_color_rule,
    register_custom_model_rule,
    MODEL_RULES,
    COLOR_MAP,
    MATERIAL_MAP
)

class TestSkuGeneratorAdversarial(unittest.TestCase):
    """Adversarial stress testing for SKU generation, collisions, and abbreviations."""

    def test_abbreviate_model_adversarial(self):
        """Test model abbreviation with empty, Chinese-only, special characters, and digits."""
        # Empty string
        self.assertEqual(abbreviate_model(""), "MOD")
        self.assertEqual(abbreviate_model("   "), "MOD")

        # Pure Chinese characters without ASCII
        self.assertEqual(abbreviate_model("华为荣耀手机"), "MOD")

        # Mixed Chinese and ASCII / Digits: Note: '红米' is not in MODEL_RULES (only 'redmi'),
        # so it falls back to first letters of ASCII words + digits: Note(N) + 13 + Pro(P) -> N13P
        self.assertEqual(abbreviate_model("红米 Note 13 Pro+"), "N13P")
        self.assertEqual(abbreviate_model("Redmi Note 13 Pro+"), "RN13PP")

        # Symbols and punctuation
        self.assertEqual(abbreviate_model("!!!Realme### Neo$$$ 8***"), "RN8")

        # Pure digits
        self.assertEqual(abbreviate_model("12345"), "12345")

        # Extremely long model name
        long_name = "Super " * 50 + "Phone 99"
        abbr = abbreviate_model(long_name)
        self.assertIsInstance(abbr, str)
        self.assertTrue(len(abbr) > 0)

    def test_abbreviate_material_adversarial(self):
        """Test material abbreviation with unknown, single letter, symbols, and empty inputs."""
        # Standard recognized
        self.assertEqual(abbreviate_material("Liquid Silicone"), "SIL")
        self.assertEqual(abbreviate_material("Tempered Glass"), "GLS")
        self.assertEqual(abbreviate_material("Hard PC"), "PC")

        # Unknown material fallback (first 3 letters)
        self.assertEqual(abbreviate_material("Titanium"), "TIT")

        # Very short unknown material (< 3 letters)
        self.assertEqual(abbreviate_material("AI"), "AIM")  # padded with MAT
        self.assertEqual(abbreviate_material(""), "MAT")

        # Symbols only
        self.assertEqual(abbreviate_material("$$$"), "MAT")

    def test_abbreviate_color_adversarial(self):
        """Test color abbreviation with unknown colors, single letters, and symbols."""
        # Standard recognized
        self.assertEqual(abbreviate_color("Antique White"), "WT")
        self.assertEqual(abbreviate_color("Classic Black"), "BK")

        # Unknown color fallback (first 2 letters)
        self.assertEqual(abbreviate_color("Ultramarine"), "UL")

        # Very short (< 2 letters)
        self.assertEqual(abbreviate_color("X"), "CO")
        self.assertEqual(abbreviate_color(""), "CO")
        self.assertEqual(abbreviate_color("@#$%"), "CO")

    def test_abbreviate_print_adversarial(self):
        """Test finish/print abbreviation with various terms and unmapped strings."""
        self.assertEqual(abbreviate_print("Floral Cartoon Artwork"), "P")
        self.assertEqual(abbreviate_print("Holographic Aurora"), "G")
        self.assertEqual(abbreviate_print("Mirror Plating"), "E")
        self.assertEqual(abbreviate_print("Frosted Magnetic"), "M")
        self.assertEqual(abbreviate_print("Plain Cube Simple"), "S")
        # Default fallback is 'S' (Solid)
        self.assertEqual(abbreviate_print(""), "S")
        self.assertEqual(abbreviate_print("random unknown text"), "S")

    def test_generate_sku_structural_integrity(self):
        """Verify SKU strictly adheres to [model]-[material]-[color]-[finish] even under extreme inputs."""
        sku = generate_sku("", "", "")
        parts = sku.split("-")
        self.assertEqual(len(parts), 4, f"SKU {sku} must have exactly 4 parts separated by hyphen")
        self.assertEqual(parts, ["MOD", "MAT", "CO", "S"])

        # Multi-hyphen input in color
        sku_hyphen = generate_sku("Realme Neo8", "Liquid Silicone", "Dark-Night-Green-Matte-Finish-Pro")
        parts_h = sku_hyphen.split("-")
        self.assertEqual(len(parts_h), 4, f"SKU {sku_hyphen} must have exactly 4 components")
        self.assertEqual(parts_h[0], "RN8")
        self.assertEqual(parts_h[1], "SIL")
        self.assertEqual(parts_h[2], "GN")
        self.assertIn(parts_h[3], ["M", "S"])

    def test_disambiguate_sku_colliding_chains(self):
        """Adversarial stress test on deep collision cascades (-V2 through -V20)."""
        existing = {"RN8-SIL-WT-S"}
        for i in range(2, 21):
            existing.add(f"RN8-SIL-WT-S-V{i}")

        # The next available disambiguation must be -V21
        result = disambiguate_sku("RN8-SIL-WT-S", existing)
        self.assertEqual(result, "RN8-SIL-WT-S-V21")

    def test_disambiguate_sku_on_already_suffixed_sku(self):
        """
        Adversarial edge case:
        If a base SKU already has a -V2 suffix (e.g. from an existing inventory record)
        and collides, verify how disambiguation behaves.
        """
        existing = {"RN8-SIL-WT-S-V2"}
        result = disambiguate_sku("RN8-SIL-WT-S-V2", existing)
        # Note: In current implementation, f"{base_sku}-V2" produces -V2-V2
        self.assertTrue(result.startswith("RN8-SIL-WT-S-V2"))
        self.assertNotIn(result, existing)

    def test_custom_rule_registration(self):
        """Verify dynamic registration of custom color and model rules (Rule 7 standard)."""
        register_custom_color_rule("mystic bronze", "MB")
        self.assertEqual(abbreviate_color("Mystic Bronze Premium"), "MB")

        register_custom_model_rule(r"customphone\s*(\d+)", r"CP\1")
        self.assertEqual(abbreviate_model("CustomPhone 99"), "CP99")


if __name__ == "__main__":
    unittest.main()
