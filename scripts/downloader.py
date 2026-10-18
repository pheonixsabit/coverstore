import os
import sys
import argparse
import urllib.request
import re
import subprocess
from typing import List, Dict, Any

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from moveon_client import MoveOnClient, sanitize_filename
from material_detector import detect_material
from translate_helper import translate_in_place
from sku_generator import generate_sku
from inventory_manager import append_downloaded_product

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_git_binary() -> str:
    """Finds git executable across PATH and known Windows locations."""
    import shutil
    git_bin = shutil.which("git")
    if git_bin:
        return git_bin
    for candidate in [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
        os.path.expandvars(r"%ProgramFiles%\Git\cmd\git.exe"),
    ]:
        if os.path.exists(candidate):
            return candidate
    return "git"

def git_commit_and_push(commit_msg: str, cwd: str = WORKSPACE_ROOT) -> bool:
    """Stages all changes, creates a descriptive commit, and pushes to GitHub main."""
    git_bin = get_git_binary()
    try:
        print("    [*] Staging changes (git add .)...")
        subprocess.run([git_bin, "add", "."], cwd=cwd, check=True)

        status_proc = subprocess.run([git_bin, "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True)
        if not status_proc.stdout.strip():
            print("    [*] Working tree clean. Nothing to commit.")
            return True

        print(f"    [*] Creating commit: {commit_msg}")
        subprocess.run([git_bin, "commit", "-m", commit_msg], cwd=cwd, check=True)

        print("    [*] Pushing to origin main...")
        subprocess.run([git_bin, "push", "origin", "main"], cwd=cwd, check=True)
        print("    [✓] Successfully committed and pushed to GitHub!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    [!] Git operation failed: {e}")
        return False
    except Exception as e:
        print(f"    [!] Error during git push: {e}")
        return False

def download_file(url: str, dest_path: str) -> bool:
    """Downloads an image from URL to local file path."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        with urllib.request.urlopen(req, timeout=20) as resp, open(dest_path, 'wb') as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"    [!] Failed to download {url}: {e}")
        return False

def select_phone_model(models: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Displays available phone models and interactively asks user to choose.
    Supports single number, comma-separated list, 'all' or 'A', or fuzzy search.
    """
    print("\n" + "="*60)
    print("  AVAILABLE PHONE MODELS FOR THIS COVER:")
    print("="*60)
    for idx, m in enumerate(models, 1):
        print(f"  [{idx}] {m['clean_name']}")
    
    if len(models) == 1:
        print(f"\n[+] Auto-selected the only available phone model: {models[0]['clean_name']}")
        return models

    print("\nOptions: Enter number (e.g. 1), comma-separated (e.g. 1,2), 'A' for all, or type model name:")
    while True:
        choice = input("Select model: ").strip()
        if not choice:
            continue
        
        # All models
        if choice.upper() == 'A':
            return models
        
        # Check comma-separated integers
        if re.match(r'^[0-9,\s]+$', choice):
            selected = []
            parts = [p.strip() for p in choice.split(',') if p.strip()]
            valid = True
            for p in parts:
                try:
                    num = int(p)
                    if 1 <= num <= len(models):
                        selected.append(models[num - 1])
                    else:
                        print(f"Number {num} is out of range (1-{len(models)}).")
                        valid = False
                except ValueError:
                    valid = False
            if valid and selected:
                return selected

        # Fuzzy name search
        matches = [m for m in models if choice.lower() in m['clean_name'].lower()]
        if matches:
            print(f"Matched {len(matches)} model(s): {[m['clean_name'] for m in matches]}")
            return matches

        print("No matching model found. Please try again.")

def main():
    parser = argparse.ArgumentParser(description="Download phone cover images from MoveOn Global for specific phone model and material.")
    parser.add_argument("--url", "-u", type=str, help="MoveOn product URL")
    parser.add_argument("--china-delivery", "-c", type=float, default=None, help="China domestic delivery fee in BDT per unit")
    parser.add_argument("--no-push", action="store_true", help="Skip automatic git commit and push to remote repository")
    args = parser.parse_args()

    url = args.url
    if not url:
        print("\n" + "="*60)
        print("   MOVEON PHONE COVER DOWNLOADER")
        print("   (Strict single-product scope - zero crawling)")
        print("="*60)
        url = input("Enter MoveOn product link: ").strip()

    if not url:
        print("No URL provided. Exiting.")
        sys.exit(1)

    print(f"\n[*] Fetching product data from MoveOn for: {url}")
    client = MoveOnClient()
    try:
        product_info = client.fetch_product(url)
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)

    title = product_info['title']
    models = product_info['models']
    gallery_images = product_info['gallery_images']
    skus_by_model = product_info['skus_by_model']

    print(f"\n[+] Product Title: {title}")
    print(f"[+] Total Gallery Images: {len(gallery_images)}")
    print(f"[+] Total Phone Models: {len(models)}")

    # 1. Detect Material
    material = detect_material(product_info, prompt_if_unknown=True)
    material_clean = sanitize_filename(material)
    print(f"[+] Material Identified: {material_clean}")

    # 2. Select Phone Model
    selected_models = select_phone_model(models)
    print(f"\n[+] Selected {len(selected_models)} model(s) to process:")
    for m in selected_models:
        print(f"   - {m['clean_name']}")

    # 3. Process each selected model
    for model_meta in selected_models:
        model_name = model_meta['clean_name']
        model_clean = sanitize_filename(model_name)
        
        # Build strictly 2 folder paths: \gallery and \sku
        base_dir = os.path.join(WORKSPACE_ROOT, model_clean, material_clean)
        gallery_dir = os.path.join(base_dir, "gallery")
        sku_dir = os.path.join(base_dir, "sku")

        os.makedirs(gallery_dir, exist_ok=True)
        os.makedirs(sku_dir, exist_ok=True)

        print(f"\n" + "-"*60)
        print(f"Processing Model: [{model_clean}] | Material: [{material_clean}]")
        print(f"Target Directory: {base_dir}")
        print("-"*60)

        # Download Gallery Images -> \gallery\
        print(f"[*] Downloading {len(gallery_images)} gallery images into \\gallery\\...")
        for idx, img_url in enumerate(gallery_images, 1):
            ext = os.path.splitext(img_url.split('?')[0])[-1] or ".jpg"
            dest_file = os.path.join(gallery_dir, f"gallery_{idx:02d}{ext}")
            download_file(img_url, dest_file)
            print(f"    [+] Saved: {dest_file}")

        # Download SKU Variant Images -> \sku\
        model_skus = skus_by_model.get(model_name, [])
        if not model_skus:
            for k, v in skus_by_model.items():
                if k.lower() == model_name.lower() or model_name.lower() in k.lower():
                    model_skus = v
                    break
        if not model_skus and len(models) == 1:
            for v in skus_by_model.values():
                model_skus.extend(v)

        print(f"\n[*] Downloading {len(model_skus)} SKU variant images into \\sku\\...")
        downloaded_images = set()
        for idx, sku in enumerate(model_skus, 1):
            img_url = sku.get('image')
            if not img_url or img_url in downloaded_images:
                continue
            downloaded_images.add(img_url)

            sku_code = generate_sku(model_name, material, sku.get('variant_label', ''), title)
            ext = os.path.splitext(img_url.split('?')[0])[-1] or ".jpg"
            dest_file = os.path.join(sku_dir, f"{sku_code}{ext}")
            download_file(img_url, dest_file)
            print(f"    [+] Saved SKU: {sku_code} -> {dest_file}")

        # In-place translation: replace original non-English images directly
        print(f"\n[*] In-place translating non-English images in \\gallery\\ and \\sku\\...")
        translate_in_place(gallery_dir, sku_dir, material=material, model_name=model_name)

        print(f"\n[✓] Completed model [{model_clean}]:")
        print(f"    Gallery Images: {len(os.listdir(gallery_dir))} in {gallery_dir}")
        print(f"    SKU Images:     {len(os.listdir(sku_dir))} in {sku_dir}")

    # 4. Automatically sync/append to inventory records (inventory.csv and inventory.xlsx)
    print("\n[*] Updating inventory records (inventory.csv / inventory.xlsx)...")
    china_delivery = args.china_delivery
    if china_delivery is None:
        try:
            china_del_str = input("Enter China domestic delivery fee in BDT per unit [default 10.0]: ").strip()
            china_delivery = float(china_del_str) if china_del_str else 10.0
        except Exception:
            china_delivery = 10.0

    try:
        append_downloaded_product(product_info, selected_models, material, url, china_del=china_delivery)
    except Exception as e:
        print(f"[!] Warning: Failed to update inventory records: {e}")

    # 5. Automatically stage, commit, and push to GitHub
    if not args.no_push:
        print("\n[*] Committing and pushing changes to GitHub...")
        model_str = ", ".join(m['clean_name'] for m in selected_models)
        commit_msg = f"feat: process {model_str} ({material_clean}) and update inventory"
        git_commit_and_push(commit_msg)

    print("\n" + "="*60)
    print("  ALL DOWNLOADS, TRANSLATIONS & SYNC COMPLETED SUCCESSFULLY")
    print("="*60)

if __name__ == "__main__":
    main()
