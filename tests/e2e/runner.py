#!/usr/bin/env python3
"""
CoverStore Unified 4-Tier E2E Test Suite Runner
Executes Tiers 1-4 and reports structured pass/fail metrics, coverage, and execution times.
"""

import os
import sys
import time
import argparse
import unittest
from typing import List, Dict, Any

# Ensure workspace root and scripts are in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(WORKSPACE_ROOT, "scripts")
TESTS_E2E_DIR = os.path.join(WORKSPACE_ROOT, "tests", "e2e")

for p in [WORKSPACE_ROOT, SCRIPTS_DIR, TESTS_E2E_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Tier Module Mapping
TIERS_MAP = {
    1: ("Tier 1: Isolated Feature Verification (26 Features)", "test_tier1_features"),
    2: ("Tier 2: Boundary Value Analysis & Edge Cases", "test_tier2_boundaries"),
    3: ("Tier 3: Pairwise Combinatorial & Cross-Feature Integration", "test_tier3_pairwise"),
    4: ("Tier 4: Real-World Workload Scenarios", "test_tier4_workloads"),
}


def run_tier(tier_num: int, verbose: int = 1, failfast: bool = False) -> Dict[str, Any]:
    """Runs a single test tier and returns structured metrics."""
    title, module_name = TIERS_MAP[tier_num]
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(module_name)

    start_time = time.perf_counter()
    stream = open(os.devnull, "w") if verbose == 0 else sys.stderr
    runner = unittest.TextTestRunner(stream=stream, verbosity=verbose, failfast=failfast)
    result = runner.run(suite)
    duration = time.perf_counter() - start_time

    return {
        "tier": tier_num,
        "title": title,
        "total": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "duration": duration,
        "success": result.wasSuccessful()
    }


def main():
    parser = argparse.ArgumentParser(description="CoverStore Unified E2E Test Runner")
    parser.add_argument(
        "--tier",
        type=str,
        default="all",
        choices=["1", "2", "3", "4", "all"],
        help="Specific tier to run (1, 2, 3, 4, or all)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=1,
        help="Increase output verbosity"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress per-test execution output"
    )
    parser.add_argument(
        "-f", "--failfast",
        action="store_true",
        help="Stop on first failure or error"
    )

    args = parser.parse_args()
    verbosity = 0 if args.quiet else args.verbose

    tiers_to_run = [1, 2, 3, 4] if args.tier == "all" else [int(args.tier)]

    print("\n" + "=" * 78)
    print("  COVERSTORE 4-TIER E2E TEST SUITE RUNNER")
    print(f"  Target: {WORKSPACE_ROOT}")
    print(f"  Tiers: {', '.join(str(t) for t in tiers_to_run)}")
    print("=" * 78 + "\n")

    overall_start = time.perf_counter()
    results = []
    all_success = True

    for t in tiers_to_run:
        print(f"[*] Running {TIERS_MAP[t][0]}...")
        metrics = run_tier(t, verbose=verbosity, failfast=args.failfast)
        results.append(metrics)
        status_sym = "[✓] PASS" if metrics["success"] else "[✗] FAIL"
        print(f"    {status_sym} - {metrics['passed']}/{metrics['total']} passed in {metrics['duration']:.2f}s\n")
        if not metrics["success"]:
            all_success = False
            if args.failfast:
                break

    total_duration = time.perf_counter() - overall_start

    # Print Summary Table
    print("\n" + "=" * 78)
    print(f"{'Tier':<8}{'Total':<8}{'Passed':<8}{'Failed':<8}{'Errors':<8}{'Duration':<10}{'Status'}")
    print("-" * 78)

    grand_total = 0
    grand_passed = 0
    grand_failed = 0
    grand_errors = 0

    for r in results:
        status = "PASSED" if r["success"] else "FAILED"
        print(f"{'Tier ' + str(r['tier']):<8}{r['total']:<8}{r['passed']:<8}{r['failed']:<8}{r['errors']:<8}{r['duration']:.2f}s{'':<4}{status}")
        grand_total += r["total"]
        grand_passed += r["passed"]
        grand_failed += r["failed"]
        grand_errors += r["errors"]

    print("-" * 78)
    print(f"{'TOTAL':<8}{grand_total:<8}{grand_passed:<8}{grand_failed:<8}{grand_errors:<8}{total_duration:.2f}s{'':<4}{'PASSED' if all_success else 'FAILED'}")
    print("=" * 78 + "\n")

    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
