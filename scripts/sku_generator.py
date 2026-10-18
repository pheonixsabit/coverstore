import re
from typing import Optional, Dict

# Known Phone Model Abbreviations
MODEL_RULES = [
    # iPhone
    (r'iphone\s*(\d+)\s*pro\s*max', r'IP\1PM'),
    (r'iphone\s*(\d+)\s*pro', r'IP\1P'),
    (r'iphone\s*(\d+)\s*plus', r'IP\1PL'),
    (r'iphone\s*(\d+)\s*mini', r'IP\1M'),
    (r'iphone\s*(\d+)', r'IP\1'),
    (r'iphone\s*se\s*(\d*)', r'IPSE\1'),
    (r'iphone\s*xr', 'IPXR'),
    (r'iphone\s*xs\s*max', 'IPXSM'),
    (r'iphone\s*xs', 'IPXS'),
    (r'iphone\s*x', 'IPX'),
    # Realme
    (r'realme\s*neo\s*(\d+)', r'RN\1'),
    (r'realme\s*gt\s*neo\s*(\d+)', r'RGTN\1'),
    (r'realme\s*gt\s*(\d+)', r'RGT\1'),
    (r'realme\s*(\d+)\s*pro\s*\+', r'R\1PP'),
    (r'realme\s*(\d+)\s*pro', r'R\1P'),
    (r'realme\s*(\d+)', r'R\1'),
    # Samsung
    (r'galaxy\s*s(\d+)\s*ultra', r'S\1U'),
    (r'galaxy\s*s(\d+)\s*plus', r'S\1P'),
    (r'galaxy\s*s(\d+)\s*\+', r'S\1P'),
    (r'galaxy\s*s(\d+)\s*fe', r'S\1FE'),
    (r'galaxy\s*s(\d+)', r'S\1'),
    (r'galaxy\s*z\s*fold\s*(\d+)', r'ZF\1'),
    (r'galaxy\s*z\s*flip\s*(\d+)', r'ZP\1'),
    (r'galaxy\s*a(\d+)', r'A\1'),
    # Xiaomi / Redmi / Poco
    (r'redmi\s*note\s*(\d+)\s*pro\s*\+', r'RN\1PP'),
    (r'redmi\s*note\s*(\d+)\s*pro', r'RN\1P'),
    (r'redmi\s*note\s*(\d+)', r'RN\1'),
    (r'redmi\s*k(\d+)\s*pro', r'RK\1P'),
    (r'redmi\s*k(\d+)', r'RK\1'),
    (r'xiaomi\s*(\d+)\s*ultra', r'MI\1U'),
    (r'xiaomi\s*(\d+)\s*pro', r'MI\1P'),
    (r'xiaomi\s*(\d+)', r'MI\1'),
    (r'poco\s*x(\d+)\s*pro', r'PX\1P'),
    (r'poco\s*f(\d+)\s*pro', r'PF\1P'),
    # Huawei / Honor
    (r'huawei\s*mate\s*(\d+)\s*pro\s*max', r'M\1PM'),
    (r'huawei\s*mate\s*(\d+)\s*pro', r'M\1P'),
    (r'huawei\s*mate\s*(\d+)\s*rs', r'M\1RS'),
    (r'huawei\s*mate\s*(\d+)', r'M\1'),
    (r'huawei\s*pura\s*(\d+)\s*ultra', r'P\1U'),
    (r'huawei\s*pura\s*(\d+)\s*pro', r'P\1P'),
    (r'huawei\s*pura\s*(\d+)', r'P\1'),
]

# Material Abbreviations
MATERIAL_MAP: Dict[str, str] = {
    'liquid silicone': 'SIL',
    'silicone': 'SIL',
    'tempered glass': 'GLS',
    'glass': 'GLS',
    'mirror electroplated glass': 'GLS',
    'tpu': 'TPU',
    'soft tpu': 'TPU',
    'leather': 'LTH',
    'pu leather': 'LTH',
    'hard pc': 'PC',
    'polycarbonate': 'PC',
    'acrylic': 'PC',
    'metal': 'MET',
    'aluminum': 'MET',
    'carbon fiber': 'CF',
    'aramid': 'CF',
}

# Color Abbreviations
COLOR_MAP = [
    (r'antique white|white|milky', 'WT'),
    (r'classic black|black|matte black|midnight', 'BK'),
    (r'grass purple|purple|lavender|violet|lilac', 'PR'),
    (r'dark night green|green|emerald|pine|mint', 'GN'),
    (r'royal blue|blue|navy|sierra blue|pacific', 'BL'),
    (r'lavender gray|gray|grey|titanium gray|silver gray', 'GY'),
    (r'camellia red|red|wine|burgundy|crimson', 'RD'),
    (r'light teal|teal|cyan|turquoise|aqua', 'TL'),
    (r'transparent|clear', 'CL'),
    (r'yellow|lemon', 'YL'),
    (r'pink|rose', 'PK'),
    (r'orange|coral', 'OR'),
    (r'brown|coffee', 'BR'),
    (r'gold', 'GD'),
    (r'silver', 'SV'),
]

# Print / Finish Abbreviations
PRINT_MAP = [
    (r'print|pattern|painting|cartoon|anime|floral|flower|art|drawing', 'P'),
    (r'gradient|aurora|holographic', 'G'),
    (r'electroplated|mirror|plating', 'E'),
    (r'matte|frosted', 'M'),
    (r'carbon|texture|textured', 'T'),
    (r'transparent|clear', 'C'),
    (r'solid|cube|simple|straight edge|plain|pure', 'S'),
]

def abbreviate_model(model_name: str) -> str:
    """Converts a phone model string to its standard abbreviation (e.g. 'Realme Neo8' -> 'RN8')."""
    cleaned = model_name.strip()
    cleaned_lower = cleaned.lower()
    
    for pattern, repl in MODEL_RULES:
        if re.search(pattern, cleaned_lower):
            return re.sub(pattern, repl, cleaned_lower, flags=re.IGNORECASE).upper()
            
    # Generic fallback: Take first letters of words + any digits
    words = re.findall(r'[a-zA-Z]+|\d+', cleaned)
    abbr = ""
    for w in words:
        if w.isdigit():
            abbr += w
        else:
            abbr += w[0].upper()
    return abbr if abbr else "MOD"

def abbreviate_material(material_name: str) -> str:
    """Converts material name to a 3-letter abbreviation (e.g. 'Liquid Silicone' -> 'SIL')."""
    lower = material_name.lower().strip()
    for k, v in MATERIAL_MAP.items():
        if k in lower:
            return v
    # Fallback to first 3 letters
    clean = re.sub(r'[^A-Za-z]', '', material_name).upper()
    return clean[:3] if len(clean) >= 3 else (clean + "MAT")[:3]

def abbreviate_color(color_name: str) -> str:
    """Converts color string to standard 2-letter abbreviation (e.g. 'Antique White' -> 'WT')."""
    lower = color_name.lower().strip()
    for pattern, code in COLOR_MAP:
        if re.search(pattern, lower):
            return code
    # Fallback to first 2 letters
    clean = re.sub(r'[^A-Za-z]', '', color_name).upper()
    return clean[:2] if len(clean) >= 2 else "CO"

def abbreviate_print(text: str) -> str:
    """
    Extracts print / pattern / finish abbreviation:
    - P: Printed / Pattern / Graphic / Artwork
    - S: Solid / Simple / Cube / Plain
    - G: Gradient
    - E: Electroplated / Mirror
    - M: Matte / Frosted
    - C: Clear / Transparent
    """
    lower = text.lower().strip()
    for pattern, code in PRINT_MAP:
        if re.search(pattern, lower):
            return code
    return 'S'

def generate_sku(model: str, material: str, color_or_variant: str, context_title: str = "") -> str:
    """
    Generates a standardized custom SKU string following the format:
    [phonemodel abbreviation]-[material abbreviation]-[color abbreviation]-[print abbreviation]
    Example: RN8-SIL-WT-S
    """
    m_abbr = abbreviate_model(model)
    mat_abbr = abbreviate_material(material)
    c_abbr = abbreviate_color(color_or_variant)
    
    # Check both variant name and product context for finish/print
    full_context = f"{context_title} {color_or_variant}"
    p_abbr = abbreviate_print(full_context)
    
    return f"{m_abbr}-{mat_abbr}-{c_abbr}-{p_abbr}"

if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("Realme Neo8", "Liquid Silicone", "Straight Edge New Model [Antique White] Rubik's Cube Liquid Silicone", "solid color cube"),
        ("Realme Neo8", "Liquid Silicone", "Straight Edge New Model [Grass Purple] Rubik's Cube Liquid Silicone", "solid color cube"),
        ("Realme Neo8", "Liquid Silicone", "Straight Edge New Model [Classic Black] Rubik's Cube Liquid Silicone", "solid color cube"),
        ("Realme Neo8", "Liquid Silicone", "Transparent", "simple clear"),
        ("iPhone 15 Pro Max", "Tempered Glass", "Electroplated Mirror Silver", "mirror finish"),
        ("iPhone 16 Pro", "TPU", "Cartoon Astronaut Pattern", "painted pattern case"),
        ("Galaxy S24 Ultra", "Leather", "Vintage Brown", "genuine leather retro")
    ]
    for m, mat, col, title in test_cases:
        sku = generate_sku(m, mat, col, title)
        print(f"[{m}] + [{mat}] + [{col[:30]}] -> {sku}")
