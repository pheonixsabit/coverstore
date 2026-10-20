import re
import sys
from typing import Optional, Dict, Set

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
    (r'honor\s*x(\d+)\s*i', r'HX\1I'),
    (r'honor\s*(\d+)\s*lite.*', r'H\1L'),
    (r'honor\s*(\d+)\s*smart.*', r'H\1S'),
    (r'honor\s*(\d+)\s*pro\s*\+', r'H\1PP'),
    (r'honor\s*(\d+)\s*pro', r'H\1P'),
    (r'honor\s*(\d+)', r'H\1'),
    (r'honor\s*magic\s*(\d+)\s*pro', r'HM\1P'),
    (r'honor\s*magic\s*(\d+)', r'HM\1'),
    (r'huawei\s*mate\s*(\d+)\s*pro\s*max', r'M\1PM'),
    (r'huawei\s*mate\s*(\d+)\s*pro', r'M\1P'),
    (r'huawei\s*mate\s*(\d+)\s*rs', r'M\1RS'),
    (r'huawei\s*mate\s*(\d+)', r'M\1'),
    (r'huawei\s*pura\s*(\d+)\s*ultra', r'P\1U'),
    (r'huawei\s*pura\s*(\d+)\s*pro', r'P\1P'),
    (r'huawei\s*pura\s*(\d+)', r'P\1'),
    (r'honor\s*x(\d+)\s*pro\s*max', r'HX\1PM'),
    (r'honor\s*x(\d+)\s*promax', r'HX\1PM'),
    (r'honor\s*x(\d+)\s*pro', r'HX\1P'),
    (r'honor\s*x(\d+)\s*gt', r'HX\1GT'),
    (r'honor\s*x(\d+)\s*i\+?', r'HX\1I'),
    (r'honor\s*x(\d+)', r'HX\1'),
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
    'pet': 'PC',
    'micro-matte': 'PC',
    'metal': 'MET',
    'aluminum': 'MET',
    'carbon fiber': 'CF',
    'aramid': 'CF',
}

# Color Abbreviations
COLOR_MAP = [
    (r'antique white|white|milky|silver white', 'WT'),
    (r'classic black|black|matte black|midnight|graphite', 'BK'),
    (r'carbon gray|carbon grey', 'CG'),
    (r'titanium gray|titanium grey|titanium', 'TG'),
    (r'peak rock|rock', 'RK'),
    (r'lavender gray', 'GY'),
    (r'grass purple|purple|lavender|violet|lilac|sunset purple', 'PR'),
    (r'dark night green|green|emerald|pine|mint|feitianqing|celadon', 'GN'),
    (r'royal blue|blue|navy|sierra blue|pacific|wave blue', 'BL'),
    (r'gray|grey|silver gray', 'GY'),
    (r'camellia red|red|wine|burgundy|crimson', 'RD'),
    (r'light teal|teal|cyan|turquoise|aqua', 'TL'),
    (r'poplar wood grain|poplar', 'PW'),
    (r'dark gray wood grain|dark wood', 'DW'),
    (r'wood grain|wood', 'WD'),
    (r'transparent|clear', 'CL'),
    (r'yellow|lemon', 'YL'),
    (r'sakura pink|pink|rose', 'PK'),
    (r'orange|coral', 'OR'),
    (r'brown|coffee', 'BR'),
    (r'gold|desert gold', 'GD'),
    (r'silver', 'SV'),
]

# Print / Finish Abbreviations
PRINT_MAP = [
    (r'\b(?:print|printed|printing|pattern|painting|cartoon|anime|floral|flower|art|drawing)\b', 'P'),
    (r'\b(?:gradient|aurora|holographic)\b', 'G'),
    (r'\b(?:electroplated|mirror|plating)\b', 'E'),
    (r'\b(?:matte|frosted|magnetic)\b', 'M'),
    (r'\b(?:carbon|texture|textured)\b', 'T'),
    (r'\b(?:transparent|clear)\b', 'C'),
    (r'\b(?:solid|cube|simple|straight edge|plain|pure)\b', 'S'),
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

def disambiguate_sku(base_sku: str, existing_skus: set) -> str:
    """
    Appends a unique disambiguation suffix (-V2, -V3, ...)
    when base_sku already exists in the provided existing_skus set.
    Prevents suffix stacking (-V2-V2) when base_sku already has a -V<N> suffix.
    """
    if not existing_skus or base_sku not in existing_skus:
        return base_sku

    # Strip existing -V<N> suffix and resume versioning from next integer
    m = re.search(r"^(.*?)-V(\d+)$", base_sku)
    if m:
        root_sku = m.group(1)
        start_version = int(m.group(2)) + 1
    else:
        root_sku = base_sku
        start_version = 2

    version = start_version
    candidate = f"{root_sku}-V{version}"
    while candidate in existing_skus:
        version += 1
        candidate = f"{root_sku}-V{version}"
    return candidate

def resolve_sku_collision(
    base_sku: str,
    existing_skus: set,
    variant_label: str = "",
    interactive: bool = True
) -> str:
    """
    Enforces Rule 7 Duplicate SKU Collision & /grill-me Standard:
    When a SKU collides with an existing SKU or another variant,
    suggests a candidate unique SKU (-V2, -V3, ...)
    and prompts user if interactive, or logs and applies candidate if non-interactive.
    """
    if not existing_skus or base_sku not in existing_skus:
        return base_sku

    candidate = disambiguate_sku(base_sku, existing_skus)
    print("\n" + "="*65)
    print(" [!] DUPLICATE SKU COLLISION DETECTED (Rule 7 /grill-me Standard)")
    print(f"     Variant Label: {variant_label or 'N/A'}")
    print(f"     Conflicting Base SKU: {base_sku}")
    print(f"     Suggested Disambiguated SKU: {candidate}")
    print("="*65)

    chosen_sku = candidate
    if interactive and sys.stdin.isatty():
        try:
            prompt_str = f"Confirm candidate unique SKU or enter custom code [{candidate}]: "
            user_input = input(prompt_str).strip()
            if user_input:
                chosen_sku = user_input.upper()
                if chosen_sku in existing_skus:
                    print(f"    [!] '{chosen_sku}' is already taken. Generating unique suffix...")
                    chosen_sku = disambiguate_sku(chosen_sku, existing_skus)
                print(f"    [✓] Accepted user SKU: '{chosen_sku}'")
            else:
                print(f"    [✓] Accepted candidate SKU: '{candidate}'")
        except (EOFError, KeyboardInterrupt):
            print(f"    [✓] Input ended. Defaulting to candidate: '{candidate}'")
            chosen_sku = candidate
    else:
        print(f"    [*] Non-interactive / pipeline mode: Applied disambiguated SKU '{candidate}'")

    return chosen_sku

def register_custom_color_rule(pattern: str, code: str) -> None:
    """Dynamically registers or updates a color abbreviation rule at highest priority (Rule 7)."""
    clean_code = code.strip().upper()
    clean_pat = pattern.strip().lower()
    regex = r'\b' + re.escape(clean_pat) + r'\b'
    COLOR_MAP.insert(0, (regex, clean_code))

def register_custom_model_rule(pattern: str, repl: str) -> None:
    """Dynamically registers or updates a model abbreviation rule at highest priority (Rule 7)."""
    MODEL_RULES.insert(0, (pattern, repl.strip().upper()))

def generate_sku(
    model: str,
    material: str,
    color_or_variant: str,
    context_title: str = "",
    existing_skus: Optional[set] = None,
    interactive: bool = False
) -> str:
    """
    Generates a standardized custom SKU string following the format:
    [phonemodel abbreviation]-[material abbreviation]-[color abbreviation]-[print abbreviation]
    Example: RN8-SIL-WT-S
    If existing_skus is provided, disambiguates collisions with -V2, -V3 suffix per Rule 7.
    """
    m_abbr = abbreviate_model(model)
    mat_abbr = abbreviate_material(material)
    c_abbr = abbreviate_color(color_or_variant)
    
    # Check both variant name and product context for finish/print
    full_context = f"{context_title} {color_or_variant}"
    p_abbr = abbreviate_print(full_context)
    
    base_sku = f"{m_abbr}-{mat_abbr}-{c_abbr}-{p_abbr}"
    if existing_skus and base_sku in existing_skus:
        return resolve_sku_collision(base_sku, existing_skus, variant_label=color_or_variant, interactive=interactive)
    return base_sku

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
