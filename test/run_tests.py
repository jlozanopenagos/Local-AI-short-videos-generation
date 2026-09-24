"""
test_layer/run_tests.py — Standalone CLI test runner for Shorts Automation pipeline.
Runs all test suites or individual layers using Python standard library unittest.
Zero mandatory external dependencies required.
"""
import sys
import time
import argparse
import unittest
from pathlib import Path

# Ensure repo root, main project, and test directory are on sys.path
TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
MAIN_DIR = REPO_ROOT / "main"
for p in [str(TEST_DIR), str(MAIN_DIR), str(REPO_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)


# Reconfigure stdout for Windows console UTF-8 support if available
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ColoredTextTestResult(unittest.TextTestResult):
    """Custom test result that prints colored status tags."""
    def addSuccess(self, test):
        super().addSuccess(test)
        if self.showAll:
            sys.stdout.write(" [PASS]\n")

    def addError(self, test, err):
        super().addError(test, err)
        if self.showAll:
            sys.stdout.write(" [ERROR]\n")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.showAll:
            sys.stdout.write(" [FAIL]\n")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.showAll:
            sys.stdout.write(f" [SKIP] ({reason})\n")


def build_suite(layer_filter: str = "all") -> unittest.TestSuite:
    """Discovers and compiles test suites based on the chosen layer filter."""
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    layers_to_run = []
    if layer_filter in ("all", "unit"):
        layers_to_run.append(("Unit Tests", TEST_DIR / "unit"))
    if layer_filter in ("all", "integration"):
        layers_to_run.append(("Integration Tests", TEST_DIR / "integration"))
    if layer_filter in ("all", "contract", "contracts"):
        layers_to_run.append(("Contract & Schema Tests", TEST_DIR / "contracts"))
    if layer_filter in ("all", "security"):
        layers_to_run.append(("Security & Privacy Tests", TEST_DIR / "security"))
    if layer_filter in ("all", "connectivity"):
        layers_to_run.append(("Connectivity Tests", TEST_DIR / "connectivity"))

    for name, directory in layers_to_run:
        if directory.exists():
            discovered = loader.discover(
                start_dir=str(directory),
                pattern="test_*.py",
                top_level_dir=str(REPO_ROOT)
            )
            suite.addTests(discovered)

    return suite


def main():
    parser = argparse.ArgumentParser(description="Shorts Automation QA Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run Layer 1: Unit Tests")
    parser.add_argument("--integration", action="store_true", help="Run Layer 2: Integration Tests")
    parser.add_argument("--contract", "--contracts", dest="contract", action="store_true", help="Run Layer 3: Contract Tests")
    parser.add_argument("--security", action="store_true", help="Run Layer 4: Security Tests")
    parser.add_argument("--connectivity", action="store_true", help="Run Layer 5: Connectivity Tests")
    parser.add_argument("-v", "--verbose", action="store_true", default=True, help="Verbose output")
    args = parser.parse_args()

    # Determine filter
    active_filters = []
    if args.unit:
        active_filters.append("unit")
    if args.integration:
        active_filters.append("integration")
    if args.contract:
        active_filters.append("contract")
    if args.security:
        active_filters.append("security")
    if args.connectivity:
        active_filters.append("connectivity")

    target_layer = active_filters[0] if len(active_filters) == 1 else "all"

    print("\n" + "=" * 70)
    print("=== SHORTS AUTOMATION: SENIOR QA TEST SUITE ===")
    print(f"Target Layer: {target_layer.upper()}")
    print("=" * 70)

    start_time = time.time()
    suite = build_suite(target_layer)
    test_count = suite.countTestCases()

    if test_count == 0:
        print(f"No tests discovered for target layer: {target_layer}")
        sys.exit(0)

    print(f"Discovered {test_count} tests across active layers.\n")

    runner = unittest.TextTestRunner(
        verbosity=2 if args.verbose else 1,
        resultclass=ColoredTextTestResult
    )
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"Execution Summary: Ran {result.testsRun} tests in {elapsed:.2f}s")
    if result.wasSuccessful():
        print("Status: ALL TESTS PASSED [OK]")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print(f"Status: FAILED (Failures: {len(result.failures)}, Errors: {len(result.errors)})")
        print("=" * 70 + "\n")
        sys.exit(1)



if __name__ == "__main__":
    main()
