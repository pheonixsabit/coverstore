#!/usr/bin/env python3
"""
CoverStore Tier 5 Adversarial Stress Test Suite Runner.
Executes deep white-box stress testing across all pipeline modules.
"""

import sys
import os
import unittest
import time

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure repository root is in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SUITES = [
    ("MoveOn & Downloader Adversarial", "tests.adversarial.test_moveon_downloader_adversarial"),
    ("Image Translator & Inpainting Adversarial", "tests.adversarial.test_image_translator_adversarial"),
    ("SKU Generator & Collisions Adversarial", "tests.adversarial.test_sku_generator_adversarial"),
    ("Inventory Manager & Formulas Adversarial", "tests.adversarial.test_inventory_manager_adversarial"),
    ("Pipeline Orchestrator Adversarial", "tests.adversarial.test_pipeline_orchestrator_adversarial"),
]

def run_adversarial_suite():
    print("=" * 78)
    print("  COVERSTORE TIER 5 ADVERSARIAL STRESS TEST RUNNER")
    print("  Scope: MoveOn, Downloader, Translator, SKU, Inventory, Orchestrator")
    print("=" * 78)

    loader = unittest.TestLoader()
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    results_table = []

    start_all = time.time()

    for name, module_path in SUITES:
        print(f"\n[*] Executing {name} ({module_path})...")
        suite = loader.loadTestsFromName(module_path)
        count = suite.countTestCases()
        total_tests += count

        runner = unittest.TextTestRunner(verbosity=1)
        t_start = time.time()
        res = runner.run(suite)
        duration = time.time() - t_start

        passed = count - len(res.failures) - len(res.errors)
        total_passed += passed
        total_failed += len(res.failures)
        total_errors += len(res.errors)

        status = "PASSED" if res.wasSuccessful() else "FAILED"
        results_table.append({
            "name": name,
            "total": count,
            "passed": passed,
            "failed": len(res.failures),
            "errors": len(res.errors),
            "duration": f"{duration:.2f}s",
            "status": status
        })

    total_duration = time.time() - start_all

    print("\n" + "=" * 78)
    print(f"{'Adversarial Suite':<45} {'Total':<7} {'Pass':<6} {'Fail':<6} {'Err':<5} {'Duration':<9} {'Status'}")
    print("-" * 78)
    for r in results_table:
        print(f"{r['name']:<45} {r['total']:<7} {r['passed']:<6} {r['failed']:<6} {r['errors']:<5} {r['duration']:<9} {r['status']}")
    print("-" * 78)
    print(f"{'TOTAL TIER 5 ADVERSARIAL TESTS':<45} {total_tests:<7} {total_passed:<6} {total_failed:<6} {total_errors:<5} {total_duration:.2f}s    {'PASSED' if total_failed + total_errors == 0 else 'FAILED'}")
    print("=" * 78 + "\n")

    return 0 if (total_failed + total_errors == 0) else 1

if __name__ == "__main__":
    sys.exit(run_adversarial_suite())
