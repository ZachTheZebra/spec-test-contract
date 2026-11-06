"""Contract checks for scripts/check_coverage.py."""

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_coverage.py"
EXAMPLE = ROOT / "examples" / "velocity-counter" / "spec_coverage.yaml"


def run_checker(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
    )


def write_case(directory, cfg_body, invariants, tests):
    root = Path(directory)
    (root / "models").mkdir()
    (root / "tests").mkdir()
    (root / "models" / "small.cfg").write_text(cfg_body, encoding="utf-8")
    (root / "Demo.tla").write_text("---- MODULE Demo ----\n====\n", encoding="utf-8")
    blocks = []
    for name, body in tests.items():
        blocks.append(f"def {name}():\n{textwrap.indent(body, '    ')}\n")
    (root / "tests" / "test_rules.py").write_text("\n".join(blocks), encoding="utf-8")
    lines = [
        "model_checker: tlc",
        "specs:",
        "  - name: Demo",
        "    tla: Demo.tla",
        "    models:",
        "      - config: models/small.cfg",
        "        invariants:",
    ]
    for name, test_names in invariants:
        rendered = ", ".join(test_names)
        lines.append(f"          - name: {name}")
        lines.append(f"            tests: [{rendered}]")
    mapping = root / "spec_coverage.yaml"
    mapping.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return mapping


class CheckCoverageTest(unittest.TestCase):
    def test_example_passes_from_another_directory(self):
        result = run_checker(["--mapping", str(EXAMPLE)], cwd=Path("/"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 model, 7 invariants, 7 tests", result.stdout)

    def test_discover_finds_the_example(self):
        result = run_checker(["--root", str(ROOT / "examples")])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("contract ok:", result.stdout)

    def test_missing_mapping_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "INVARIANT Kept\nINVARIANT Forgotten\n",
                [("Kept", ["test_kept"])],
                {"test_kept": "assert True"},
            )
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(
            "FAIL missing mapping: Demo models/small.cfg invariant Forgotten is not in the contract",
            result.stdout,
        )

    def test_stale_mapping_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "INVARIANT Kept\n",
                [("Kept", ["test_kept"]), ("Retired", ["test_retired"])],
                {"test_kept": "assert True", "test_retired": "assert True"},
            )
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL stale mapping:", result.stdout)
        self.assertIn("Retired", result.stdout)

    def test_missing_test_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "INVARIANT Kept\n",
                [("Kept", ["test_kept"])],
                {},
            )
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL missing test: test_kept for invariant Kept", result.stdout)

    def test_failing_test_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "INVARIANT Kept\n",
                [("Kept", ["test_kept"])],
                {"test_kept": "assert False, 'window moved'"},
            )
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL test test_kept: window moved", result.stdout)

    def test_comment_and_property_are_not_contract_invariants(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "\\* INVARIANT NotReal\nINVARIANT Kept\nPROPERTY Completion\n",
                [("Kept", ["test_kept"])],
                {"test_kept": "assert True"},
            )
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PROPERTY Completion", result.stdout)
        self.assertNotIn("NotReal", result.stdout)

    def test_empty_tree_exits_two(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_checker(["--root", directory])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
