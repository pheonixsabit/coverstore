import re
from typing import Optional, List, Dict, Any

KNOWN_MATERIALS = [
    {
        'canonical': 'Liquid Silicone',
        'patterns': [r'liquid silicone', r'liquid rubber', r'rubik\'s cube liquid silicone']
    },
    {
        'canonical': 'Silicone',
        'patterns': [r'\bsilicone\b', r'\bsilicon\b', r'\bsoft silicone\b']
    },
    {
        'canonical': 'Tempered Glass',
        'patterns': [r'tempered glass', r'electroplated glass', r'mirror glass', r'\bglass\b']
    },
    {
        'canonical': 'TPU',
        'patterns': [r'\btpu\b', r'thermoplastic polyurethane', r'\bsoft tpu\b']
    },
    {
        'canonical': 'Leather',
        'patterns': [r'\bleather\b', r'pu leather', r'genuine leather', r'vegan leather']
    },
    {
        'canonical': 'Hard PC',
        'patterns': [r'hard pc', r'polycarbonate', r'\bacrylic\b', r'hard plastic', r'hard case']
    },
    {
        'canonical': 'Metal',
        'patterns': [r'\bmetal\b', r'\baluminum\b', r'alloy']
    },
    {
        'canonical': 'Carbon Fiber',
        'patterns': [r'carbon fiber', r'aramid', r'aramid fiber', r'kevlar']
    }
]

def detect_material_from_text(text: str) -> Optional[str]:
    """Scans text for known phone case materials in order of specificity."""
    if not text:
        return None
    lower_text = text.lower()
    for mat in KNOWN_MATERIALS:
        for pat in mat['patterns']:
            if re.search(pat, lower_text):
                return mat['canonical']
    return None

def detect_material(product_info: Dict[str, Any], prompt_if_unknown: bool = True) -> str:
    """
    Attempts to auto-detect the phone cover material from product title and properties.
    If not recognized and prompt_if_unknown is True, interactively prompts the user.
    """
    title = product_info.get('title', '')
    mat = detect_material_from_text(title)
    if mat:
        return mat

    # Check properties
    for prop in product_info.get('properties', []):
        prop_name = prop.get('name', '')
        if any(k in prop_name.lower() for k in ['material', 'texture', 'craft']):
            for val in prop.get('values', {}).get('data', []):
                val_name = val.get('name', '')
                mat = detect_material_from_text(val_name)
                if mat:
                    return mat

    # If unrecognized and prompt is enabled
    if prompt_if_unknown:
        print("\n" + "="*50)
        print("  [!] Cover material could not be auto-detected.")
        print(f"  Product Title: {title}")
        print("="*50)
        print("Select or enter the material for this phone cover:")
        print("  [1] Liquid Silicone")
        print("  [2] Silicone")
        print("  [3] TPU (Soft Plastic)")
        print("  [4] Tempered Glass")
        print("  [5] Leather")
        print("  [6] Hard PC (Polycarbonate)")
        print("  [7] Enter custom material name")
        
        while True:
            choice = input("Enter choice (1-7): ").strip()
            if choice == "1":
                return "Liquid Silicone"
            elif choice == "2":
                return "Silicone"
            elif choice == "3":
                return "TPU"
            elif choice == "4":
                return "Tempered Glass"
            elif choice == "5":
                return "Leather"
            elif choice == "6":
                return "Hard PC"
            elif choice == "7":
                custom = input("Enter material name: ").strip()
                if custom:
                    return custom
            else:
                print("Invalid selection. Please choose 1-7.")
    
    return "Generic Material"
