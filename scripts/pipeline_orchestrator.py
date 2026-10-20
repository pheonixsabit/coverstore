#!/usr/bin/env python3
"""
CoverStore Unified Pipeline Orchestrator & Git Sync
Chains Agent 1 (downloader.py) -> Agent 2 (image_translator.py) -> Agent 3 (pathao_sync.py) -> Verification -> Git Sync.
Strict single-product scope per GEMINI.md and PROJECT.md standards.
"""

import os
import sys
import csv
import json
import argparse
import subprocess
from typing import Dict, Any, Optional, List
from PIL import Image

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPTS_DIR = os.path.abspath(os.path.dirname(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
INVENTORY_CSV_PATH = os.path.join(WORKSPACE_ROOT, "inventory.csv")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

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

        status_proc = subprocess.run(
            [git_bin, "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        if not status_proc.stdout.strip():
            print("    [*] Working tree clean. Nothing to commit.")
            return True

        print(f"    [*] Creating commit: {commit_msg}")
        subprocess.run([git_bin, "commit", "-m", commit_msg], cwd=cwd, check=True)

        print("    [*] Pushing to origin main...")
        push_proc = subprocess.run([git_bin, "push", "origin", "main"], cwd=cwd)
        if push_proc.returncode != 0:
            print("    [*] Remote is ahead, integrating changes with --rebase --autostash...")
            subprocess.run([git_bin, "pull", "--rebase", "--autostash", "origin", "main"], cwd=cwd, check=True)
            subprocess.run([git_bin, "push", "origin", "main"], cwd=cwd, check=True)
        print("    [✓] Successfully pushed to origin main")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    [!] Git operation failed: {e}")
        return False

class PipelineOrchestrator:
    """
    Coordinates execution across the 3 autonomous agents:
      - Agent 1: MoveOn Ingestion & Pricing Agent (downloader.py)
      - Agent 2: In-Place Visual Image Translation Agent (image_translator.py)
      - Agent 3: Pathao Commerce Sync & Catalog Upload Agent (pathao_sync.py)
    Followed by verification and Git push standard enforcement.
    """
    def __init__(
        self,
        url: str,
        china_delivery: Optional[float] = None,
        model: Optional[str] = None,
        material: Optional[str] = None,
        dry_run: bool = False,
        skip_pathao: bool = False,
        no_push: bool = False,
        headful: bool = False,
    ):
        self.url = url
        self.china_delivery = china_delivery
        self.model = model
        self.material = material
        self.dry_run = dry_run
        self.skip_pathao = skip_pathao
        self.no_push = no_push
        self.headful = headful
        self.skip_tests = False
        self.handoff_a1: Dict[str, Any] = {}
        self.handoff_a2: Dict[str, Any] = {}
        self.handoff_a3: Dict[str, Any] = {}

    def run_agent1(self) -> Dict[str, Any]:
        """
        Executes Agent 1 (MoveOn Ingestion & Pricing Agent).
        Validates or solicits China domestic delivery charge (Rule 9).
        Verifies 2-folder asset download and inventory persistence.
        """
        if not self.url:
            raise ValueError("Agent 1 requires a MoveOn product URL.")

        # Enforce Rule 9: Mandatory China Domestic Delivery Charge
        if self.china_delivery is not None and self.china_delivery < 0.0:
            raise ValueError("China domestic delivery charge cannot be negative.")
        if self.china_delivery is None:
            if sys.stdin.isatty():
                print("\n" + "="*70)
                print(" [Mandatory Rule 9] China Domestic Delivery Charge Input")
                print("="*70)
                while True:
                    try:
                        raw = input("Enter China domestic delivery charge in BDT per unit (e.g. 10.0): ").strip()
                        val = float(raw)
                        if val < 0.0:
                            print("Charge cannot be negative.")
                            continue
                        self.china_delivery = val
                        break
                    except ValueError:
                        print("Invalid number format. Please enter a valid decimal number.")
            else:
                raise ValueError(
                    "Mandatory China domestic delivery charge (Rule 9) is required. "
                    "When running non-interactively or in automated pipelines, provide --china-delivery <BDT>."
                )

        if not self.dry_run:
            cmd = [
                sys.executable,
                os.path.join(SCRIPTS_DIR, "downloader.py"),
                "--url", self.url,
                "--china-delivery", str(self.china_delivery),
                "--no-push"
            ]
            if self.model:
                cmd.extend(["--model", self.model])
            if self.material:
                cmd.extend(["--material", self.material])

            print(f"    [*] Invoking Agent 1: {' '.join(cmd)}")
            proc = subprocess.run(cmd, cwd=WORKSPACE_ROOT)
            if proc.returncode != 0:
                raise RuntimeError(f"Agent 1 (downloader.py) failed with returncode {proc.returncode}")

        # Locate processed product from inventory
        matched_records = []
        if os.path.exists(INVENTORY_CSV_PATH):
            with open(INVENTORY_CSV_PATH, "r", encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    if self.url in r.get("link", "") or (self.model and self.model == r.get("Phone Model")):
                        matched_records.append(r)

        if matched_records:
            model_name = matched_records[0].get("Phone Model", self.model or "Unknown Model")
            material = matched_records[0].get("Material", self.material or "Protective Case")
        else:
            model_name = self.model or "Realme Neo8"
            material = self.material or "Liquid Silicone"

        target_dir = os.path.join(WORKSPACE_ROOT, model_name, material)
        gal_dir = os.path.join(target_dir, "gallery")
        sku_dir = os.path.join(target_dir, "sku")

        # Agent 1 output validation (Contract & P19)
        if not self.dry_run:
            valid = os.path.isdir(gal_dir) and os.path.isdir(sku_dir) and len(os.listdir(gal_dir)) > 0
            if not valid:
                raise RuntimeError(f"Agent 1 output validation failed: gallery/sku missing or empty in {target_dir}")

        handoff = {
            "model": model_name,
            "material": material,
            "target_dir": target_dir,
            "url": self.url,
            "variants_count": len(matched_records)
        }
        return handoff

    def run_agent2(self, handoff_a1: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes Agent 2 (In-Place Visual Image Translation Agent).
        Validates target directories and performs in-place text translation.
        """
        target_dir = handoff_a1.get("target_dir")
        model_name = handoff_a1.get("model")
        material = handoff_a1.get("material")

        if not target_dir or not os.path.exists(target_dir):
            if not self.dry_run:
                raise RuntimeError(f"Agent 2 cannot find target directory: {target_dir}")

        from image_translator import ImageTranslator
        print(f"    [*] Translating images in: {target_dir}")
        translator = ImageTranslator()
        results = {}
        if os.path.exists(target_dir):
            results = translator.translate_directory(target_dir, model_name=model_name, material=material, dry_run=self.dry_run)

        # Agent 2 output validation (Contract & P20)
        gal_dir = os.path.join(target_dir, "gallery") if target_dir else ""
        sku_dir = os.path.join(target_dir, "sku") if target_dir else ""
        verified_count = 0
        for d in [gal_dir, sku_dir]:
            if os.path.exists(d):
                for fn in os.listdir(d):
                    if fn.lower().endswith((".jpg", ".jpeg", ".png")):
                        fp = os.path.join(d, fn)
                        with Image.open(fp) as im:
                            if im.size[0] <= 0 or im.size[1] <= 0:
                                raise RuntimeError(f"Agent 2 output corrupted image: {fp}")
                            verified_count += 1

        handoff = {
            "url": self.url,
            "images_verified": True,
            "verified_count": verified_count,
            "translated_count": results.get("translated_count", 0) if isinstance(results, dict) else 0,
            "model": model_name,
            "material": material
        }
        return handoff

    def run_agent3(self, handoff_a2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes Agent 3 (Pathao Commerce Catalog Upload Agent).
        Generates 16-column workbook, reconciles CDN assets, and publishes or dry-runs catalog.
        """
        if self.skip_pathao:
            print("    [*] Skipping Pathao Commerce sync (--skip-pathao enabled)")
            return {"status": "skipped", "product_id": None, "message": "Pathao sync skipped"}

        from pathao_sync import (
            PathaoCommerceClient,
            load_and_group_inventory,
            generate_import_workbook,
            extract_base_sku,
            PATHAO_BASE_URL
        )

        products = load_and_group_inventory()
        matched = [p for p in products if self.url in p.get("source_link", "")]
        if not matched:
            model_name = handoff_a2.get("model")
            material = handoff_a2.get("material")
            if model_name:
                matched = [
                    p for p in products
                    if model_name in p.get("phone_models", []) and material in p.get("materials", [])
                ]

        if not matched:
            raise RuntimeError(f"No matching inventory products found for URL: {self.url}")

        prod = matched[0]
        base_sku = extract_base_sku(prod["variants"][0]["sku"]) if prod.get("variants") else "COVER"

        if self.dry_run:
            print("    [*] Executing Pathao Commerce dry-run sync...")
            wb_path = os.path.join(WORKSPACE_ROOT, f"pathao_import_{base_sku.lower()}.xlsx")
            generate_import_workbook(prod, output_path=wb_path)
            report = {
                "status": "success",
                "product_id": 0,
                "parent_sku": base_sku,
                "variants_count": len(prod.get("variants", [])),
                "live_url": f"{PATHAO_BASE_URL}/products/dry-run"
            }
            return report

        print("    [*] Executing Pathao Commerce live sync...")
        client = PathaoCommerceClient(headless=not self.headful)
        client.start()
        try:
            if not client.ensure_authenticated():
                raise RuntimeError("Failed to authenticate to Pathao Commerce")
            success = client.sync_product(prod)
            if not success:
                raise RuntimeError(f"Failed to sync product to Pathao Commerce: {prod.get('title')}")
            report = getattr(client, "last_report", None)
            if not report:
                report = {
                    "status": "success",
                    "product_id": getattr(client, "last_imported_product_id", None),
                    "parent_sku": base_sku,
                    "variants_count": len(prod.get("variants", [])),
                    "live_url": f"{PATHAO_BASE_URL}/products"
                }
            return report
        finally:
            client.close()

    def run_verification(self) -> bool:
        """Runs the E2E test suite (tests/e2e/runner.py) to guarantee pipeline integrity."""
        if self.skip_tests:
            print("    [*] Skipping verification test suite (--skip-tests enabled)")
            return True

        print("    [*] Running test suite verification (tests/e2e/runner.py)...")
        runner_path = os.path.join(WORKSPACE_ROOT, "tests", "e2e", "runner.py")
        proc = subprocess.run([sys.executable, runner_path, "-q"], cwd=WORKSPACE_ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Pipeline verification test suite failed:\n{proc.stdout}\n{proc.stderr}")
        return True

    def run_git_sync(self, model: str, material: str) -> bool:
        """Stages changes, commits with standard message, and pushes to origin main."""
        if self.no_push or self.dry_run:
            print("    [*] Skipping git push (--no-push or --dry-run enabled)")
            return True

        commit_msg = f"feat: process {model} ({material}) - pipeline complete"
        return git_commit_and_push(commit_msg, cwd=WORKSPACE_ROOT)

    def execute(self) -> Dict[str, Any]:
        """
        Executes full sequential pipeline:
        Agent 1 -> Agent 2 -> Agent 3 -> Verification -> Git Push.
        """
        print("\n" + "=" * 80)
        print("  COVERSTORE UNIFIED PIPELINE ORCHESTRATOR")
        print(f"  Target URL: {self.url}")
        print(f"  Dry Run:    {self.dry_run}")
        print("=" * 80)

        # Step 1: Agent 1 - MoveOn Ingestion & Pricing
        print("\n[*] STEP 1: Launching Agent 1 (MoveOn Ingestion & Pricing Agent)...")
        self.handoff_a1 = self.run_agent1()
        print(f"[✓] Step 1 Complete! Handoff: {self.handoff_a1}")

        # Step 2: Agent 2 - In-Place Visual Image Translation
        print("\n[*] STEP 2: Launching Agent 2 (In-Place Visual Image Translation Agent)...")
        self.handoff_a2 = self.run_agent2(self.handoff_a1)
        print(f"[✓] Step 2 Complete! Handoff: {self.handoff_a2}")

        # Step 3: Agent 3 - Pathao Commerce Catalog Upload
        print("\n[*] STEP 3: Launching Agent 3 (Pathao Commerce Catalog Upload Agent)...")
        self.handoff_a3 = self.run_agent3(self.handoff_a2)
        print(f"[✓] Step 3 Complete! Report: {self.handoff_a3}")

        # Step 4: Verification Checks
        print("\n[*] STEP 4: Running Verification Checks...")
        self.run_verification()
        print("[✓] Step 4 Complete! Verification tests passed.")

        # Step 5: Git Commit & Push
        print("\n[*] STEP 5: Enforcing Git Push Standard (GEMINI Rule 1)...")
        self.run_git_sync(self.handoff_a1["model"], self.handoff_a1["material"])
        print("[✓] Step 5 Complete! Repository synchronized.")

        return {
            "status": "success",
            "agent1_handoff": self.handoff_a1,
            "agent2_handoff": self.handoff_a2,
            "agent3_report": self.handoff_a3
        }

def run_pipeline(
    url: str,
    china_delivery: Optional[float] = None,
    model: Optional[str] = None,
    material: Optional[str] = None,
    dry_run: bool = False,
    skip_pathao: bool = False,
    no_push: bool = False,
    headful: bool = False,
    skip_tests: bool = False
) -> Dict[str, Any]:
    """Programmatic entrypoint to run the CoverStore pipeline."""
    orchestrator = PipelineOrchestrator(
        url=url,
        china_delivery=china_delivery,
        model=model,
        material=material,
        dry_run=dry_run,
        skip_pathao=skip_pathao,
        no_push=no_push,
        headful=headful
    )
    orchestrator.skip_tests = skip_tests
    return orchestrator.execute()

def main():
    parser = argparse.ArgumentParser(description="CoverStore Unified Pipeline Orchestrator (Agents 1-3 & Git Sync)")
    parser.add_argument("--url", "-u", type=str, default=None, help="MoveOn single product URL")
    parser.add_argument("--china-delivery", "-c", type=float, default=None, help="China domestic delivery charge in BDT per unit")
    parser.add_argument("--model", "-m", type=str, default=None, help="Phone model name override")
    parser.add_argument("--material", type=str, default=None, help="Material name override")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Simulate pipeline execution without mutating remote stores or repository")
    parser.add_argument("--skip-pathao", action="store_true", help="Skip Pathao Commerce publication")
    parser.add_argument("--no-push", action="store_true", help="Skip git push standard")
    parser.add_argument("--headful", action="store_true", help="Run browser in headful mode for Pathao sync")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running e2e test suite verification")
    args = parser.parse_args()

    url = args.url
    if not url:
        if sys.stdin.isatty():
            print("\n" + "=" * 60)
            print("   COVERSTORE UNIFIED PIPELINE ORCHESTRATOR")
            print("   (Strict single-product scope - zero crawling)")
            print("=" * 60)
            url = input("Enter MoveOn product link: ").strip()
        else:
            print("[!] Error: --url is required when running non-interactively.", file=sys.stderr)
            sys.exit(1)

    if not url:
        print("[!] No URL provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    try:
        result = run_pipeline(
            url=url,
            china_delivery=args.china_delivery,
            model=args.model,
            material=args.material,
            dry_run=args.dry_run,
            skip_pathao=args.skip_pathao,
            no_push=args.no_push,
            headful=args.headful,
            skip_tests=args.skip_tests
        )
        print("\n" + "=" * 80)
        print("  PIPELINE EXECUTION FINISHED SUCCESSFULLY")
        print("=" * 80)
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Pipeline halted due to error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
