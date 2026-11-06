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
        lines.append(f"          - name: {name}")
        if test_names == "tlc":
            lines.append("            checked_by: tlc")
            continue
        rendered = ", ".join(test_names)
        lines.append(f"            tests: [{rendered}]")
    mapping = root / "spec_coverage.yaml"
    mapping.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return mapping


class CheckCoverageTest(unittest.TestCase):
    def test_example_passes_from_another_directory(self):
        result = run_checker(["--mapping", str(EXAMPLE)], cwd=Path("/"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 model, 7 invariants, 6 tests", result.stdout)

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

    def test_tlc_owned_invariant_needs_no_test(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "INVARIANT TypeOK\nINVARIANT Kept\n",
                [("TypeOK", "tlc"), ("Kept", ["test_kept"])],
                {"test_kept": "assert True"},
            )
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 model, 2 invariants, 1 test", result.stdout)

    def test_tlc_owned_invariant_cannot_vanish(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "INVARIANT TypeOK\nINVARIANT Kept\n",
                [("Kept", ["test_kept"])],
                {"test_kept": "assert True"},
            )
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("invariant TypeOK is not in the contract", result.stdout)

    def test_checked_by_tlc_rejects_a_test_list(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "INVARIANT TypeOK\n",
                [("TypeOK", "tlc")],
                {},
            )
            text = mapping.read_text(encoding="utf-8")
            text = text.replace("checked_by: tlc", "checked_by: tlc\n            tests: [test_type_ok]")
            mapping.write_text(text, encoding="utf-8")
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("has no test list", result.stderr)

    def test_shared_sole_test_is_a_note(self):
        with tempfile.TemporaryDirectory() as directory:
            mapping = write_case(
                directory,
                "INVARIANT WindowBoundary\nINVARIANT ExpiredNotCounted\n",
                [("WindowBoundary", ["test_window"]), ("ExpiredNotCounted", ["test_window"])],
                {"test_window": "assert True"},
            )
            result = run_checker(["--mapping", str(mapping)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "note: test_window is the only test for WindowBoundary, ExpiredNotCounted",
            result.stdout,
        )

    def test_empty_tree_exits_two(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_checker(["--root", directory])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
