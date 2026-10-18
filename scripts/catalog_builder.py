import os
import shutil
import hashlib
from typing import List, Dict, Set, Any, Tuple
from PIL import Image

def get_file_hash(filepath: str) -> str:
    """Calculates MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def build_cataloge(base_dir: str, root_cataloge: bool = True) -> Dict[str, Any]:
    """
    Builds the \\cataloge\\ directory containing:
    1. Original pictures with NO text.
    2. Translated pictures with English text.
    3. All duplicates removed (prioritizing custom SKU codes).
    """
    orig_dir = os.path.join(base_dir, "original")
    sku_dir = os.path.join(base_dir, "sku")
    trans_dir = os.path.join(base_dir, "translated")
    cat_dir = os.path.join(base_dir, "cataloge")

    os.makedirs(cat_dir, exist_ok=True)

    # 1. Identify clean original images (no text)
    # In our pipeline, original_05 has no text, whereas original_01..04 had text banners.
    # More generally, any original image that does not have a translated counterpart or is clean.
    clean_originals = []
    if os.path.exists(orig_dir):
        for f in os.listdir(orig_dir):
            if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue
            orig_path = os.path.join(orig_dir, f)
            trans_path = os.path.join(trans_dir, f"translated_{f}")
            # If no translated version was generated, it was already clean (no text)
            if not os.path.exists(trans_path):
                clean_originals.append(orig_path)

    # 2. Collect all translated images
    translated_images = []
    if os.path.exists(trans_dir):
        for f in os.listdir(trans_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                translated_images.append(os.path.join(trans_dir, f))

    # 3. Combine candidates
    all_candidates = clean_originals + translated_images

    # 4. Deduplicate based on content hash
    # Priority: SKU-coded names > clean originals > generic translated names
    def priority_score(path: str) -> int:
        fname = os.path.basename(path)
        if any(code in fname for code in ['-SIL-', '-GLS-', '-TPU-', '-LTH-', '-PC-', '-MET-']):
            return 3  # Highest priority: specific custom SKU filename
        if fname.startswith("original_"):
            return 2  # Clean original photo
        return 1      # Generic translated gallery image

    # Group by hash
    hash_map: Dict[str, List[str]] = {}
    for p in all_candidates:
        h = get_file_hash(p)
        if h not in hash_map:
            hash_map[h] = []
        hash_map[h].append(p)

    selected_files = []
    duplicates_removed = []

    for h, file_list in hash_map.items():
        # Sort by priority score descending
        file_list.sort(key=priority_score, reverse=True)
        winner = file_list[0]
        selected_files.append(winner)
        if len(file_list) > 1:
            for dup in file_list[1:]:
                duplicates_removed.append((os.path.basename(dup), os.path.basename(winner)))

    # Clear catalog directory to avoid stale files
    for existing in os.listdir(cat_dir):
        try:
            os.remove(os.path.join(cat_dir, existing))
        except Exception:
            pass

    # Copy unique files to cataloge
    catalog_files = []
    for src in selected_files:
        fname = os.path.basename(src)
        # Simplify filename: strip 'translated_' prefix for SKU files if desired or keep clean
        dest_name = fname.replace("translated_", "") if "-SIL-" in fname or "-GLS-" in fname or "-TPU-" in fname else fname
        dest_path = os.path.join(cat_dir, dest_name)
        shutil.copy2(src, dest_path)
        catalog_files.append(dest_path)

    # Also sync to workspace root \cataloge if requested
    workspace_root = os.path.abspath(os.path.join(base_dir, "..", ".."))
    root_cat_dir = os.path.join(workspace_root, "cataloge")
    if root_cataloge:
        os.makedirs(root_cat_dir, exist_ok=True)
        for cat_file in catalog_files:
            fname = os.path.basename(cat_file)
            shutil.copy2(cat_file, os.path.join(root_cat_dir, fname))

    return {
        'catalog_dir': cat_dir,
        'root_catalog_dir': root_cat_dir if root_cataloge else None,
        'clean_originals': [os.path.basename(p) for p in clean_originals],
        'total_catalog_images': len(catalog_files),
        'duplicates_removed': duplicates_removed,
        'catalog_files': catalog_files
    }

if __name__ == "__main__":
    base = r"e:\Projects\inventory\Realme Neo8\Liquid Silicone"
    result = build_cataloge(base, root_cataloge=True)
    print("Catalog Directory:", result['catalog_dir'])
    print("Clean Originals Added:", result['clean_originals'])
    print("Total Catalog Images:", result['total_catalog_images'])
    print("Duplicates Removed:", len(result['duplicates_removed']))
    for dup, kept in result['duplicates_removed']:
        print(f"  - Removed duplicate '{dup}' (Kept: '{kept}')")
    print("\nFiles in Cataloge:")
    for f in os.listdir(result['catalog_dir']):
        print(f"  + {f}")
