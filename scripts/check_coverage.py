#!/usr/bin/env python3
"""Check a spec-to-test contract.

Every INVARIANT in a mapped TLC config must appear in spec_coverage.yaml,
and every mapped Python test must exist and pass. Exit 1 on a contract
gap. Exit 2 when a file or the schema cannot be read.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "PyYAML is required. From the repo root, run: pip install -r requirements.txt\n"
    )
    raise SystemExit(2)

TLC_URL = "https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar"
SKIP_DIRS = {
    ".git",
    ".venv",
    ".tools",
    "__pycache__",
    "node_modules",
    "traces",
}
INVARIANT_KEYWORDS = {"INVARIANT", "INVARIANTS"}
PROPERTY_KEYWORDS = {"PROPERTY", "PROPERTIES"}


class ContractError(Exception):
    """The mapping file is missing or does not match the schema."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def plural(count: int, singular: str) -> str:
    word = singular if count == 1 else singular + "s"
    return f"{count} {word}"


def display(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


def discover(root: Path) -> List[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.startswith(".")]
        if "spec_coverage.yaml" in filenames:
            found.append(Path(dirpath) / "spec_coverage.yaml")
    return sorted(found)


def _names_after(keyword_set, text: str) -> List[str]:
    names: List[str] = []
    for raw in text.splitlines():
        code = raw.split("\\*")[0].strip()
        if not code or code.startswith("(*"):
            continue
        parts = code.split()
        if parts and parts[0].upper() in keyword_set:
            names.extend(parts[1:])
    return names


def _unique(names: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def invariant_names(text: str) -> List[str]:
    return _unique(_names_after(INVARIANT_KEYWORDS, text))


def property_names(text: str) -> List[str]:
    return _unique(_names_after(PROPERTY_KEYWORDS, text))


def load_mapping(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ContractError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{path} must be a mapping")
    specs = data.get("specs")
    if not isinstance(specs, list) or not specs:
        raise ContractError(f"{path} needs a non-empty specs list")
    for spec in specs:
        if not isinstance(spec, dict):
            raise ContractError(f"{path} has a spec that is not a mapping")
        for field in ("name", "tla", "models"):
            if field not in spec:
                raise ContractError(f"{path} spec is missing {field}")
        if not isinstance(spec["models"], list) or not spec["models"]:
            raise ContractError(f"{path} spec {spec.get('name')} needs a models list")
        for model in spec["models"]:
            if not isinstance(model, dict):
                raise ContractError(f"{path} has a model that is not a mapping")
            if "config" not in model or "invariants" not in model:
                raise ContractError(f"{path} model is missing config or invariants")
            if not isinstance(model["invariants"], list):
                raise ContractError(f"{path} invariants must be a list")
            for item in model["invariants"]:
                if not isinstance(item, dict) or "name" not in item:
                    raise ContractError(f"{path} each invariant needs a name")
                _require_invariant_owner(path, item)
    return data


def _require_invariant_owner(path: Path, item: dict) -> None:
    name = item.get("name")
    checked_by = item.get("checked_by")
    has_tests = "tests" in item
    if checked_by == "tlc":
        if has_tests:
            raise ContractError(f"{path} invariant {name} is checked by TLC and has no test list")
        return
    if checked_by is not None:
        raise ContractError(f"{path} invariant {name} checked_by must be tlc")
    tests = item.get("tests")
    if not isinstance(tests, list) or not all(isinstance(test, str) for test in tests):
        raise ContractError(f"{path} invariant {name} needs tests or checked_by: tlc")


def index_tests(tests_root: Path) -> Dict[str, Path]:
    """Module-level functions in tests_root, keyed by function name."""
    found: Dict[str, Path] = {}
    if not tests_root.is_dir():
        return found
    for path in sorted(tests_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                found.setdefault(node.name, path)
    return found


def run_python_test(path: Path, name: str, cache: Dict[Path, object]) -> Optional[str]:
    module = cache.get(path)
    if module is None:
        spec = importlib.util.spec_from_file_location(f"spec_contract_{path.stem}", path)
        if spec is None or spec.loader is None:
            return f"FAIL test {name}: could not load {path}"
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            return f"FAIL test {name}: import {type(exc).__name__}: {exc}"
        cache[path] = module
    function = getattr(module, name, None)
    if function is None or not callable(function):
        return f"FAIL test {name}: {path} has no function {name}"
    signature = inspect.signature(function)
    required = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.default is inspect.Parameter.empty
        and parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    if required:
        return f"FAIL test {name}: requires parameters; the checker calls tests with none"
    try:
        function()
    except AssertionError as exc:
        return f"FAIL test {name}: {exc or 'assertion failed'}"
    except Exception as exc:
        return f"FAIL test {name}: {type(exc).__name__}: {exc}"
    return None


def java_works(java: str) -> bool:
    try:
        completed = subprocess.run(
            [java, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return False
    return completed.returncode == 0


def ensure_jar(path: Path) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading tla2tools.jar (TLA+ 1.7.4) to {path}")
    urllib.request.urlretrieve(TLC_URL, path)


def run_tlc(java: str, jar: Path, tla: Path, cfg: Path) -> Optional[str]:
    metadir = tempfile.mkdtemp(prefix="tlc-")
    log_path = Path(metadir) / "tlc.log"
    command = [
        java,
        "-XX:+UseParallelGC",
        "-cp",
        str(jar),
        "tlc2.TLC",
        "-workers",
        "1",
        "-fpmem",
        "0.1",
        "-nowarning",
        "-cleanup",
        "-metadir",
        metadir,
        "-config",
        str(cfg.resolve()),
        tla.name,
    ]
    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            completed = subprocess.run(
                command,
                cwd=str(tla.parent),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=180,
            )
        log = log_path.read_text(encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return "TLC timed out after 180s"
    finally:
        shutil.rmtree(metadir, ignore_errors=True)
    if completed.returncode != 0 or "No error has been found" not in log:
        tail = "\n".join(log.strip().splitlines()[-20:])
        return f"TLC rejected the model\n{tail}"
    return None


def check_mapping(
    mapping_path: Path,
    data: dict,
    run_tlc_models: bool,
    java: str,
    jar: Path,
) -> Tuple[List[str], int, int, int]:
    failures: List[str] = []
    base = mapping_path.parent
    tests_root_value = data.get("tests_root") or "tests"
    tests_root = (base / tests_root_value).resolve()
    tests = index_tests(tests_root)
    loaded: Dict[Path, object] = {}
    ran: set = set()
    model_count = 0
    invariant_count = 0
    want_tlc = run_tlc_models and data.get("model_checker", "tlc") == "tlc"

    for spec in data["specs"]:
        spec_name = spec["name"]
        tla_path = (base / spec["tla"]).resolve()
        for model in spec["models"]:
            model_count += 1
            cfg_path = (base / model["config"]).resolve()
            cfg_display = f"{spec_name} {display(cfg_path, base)}"
            if not cfg_path.is_file():
                failures.append(f"FAIL missing config: {cfg_display}")
                continue
            cfg_text = cfg_path.read_text(encoding="utf-8")
            declared = invariant_names(cfg_text)
            for prop in property_names(cfg_text):
                print(
                    f"note: PROPERTY {prop} in {cfg_display} is a TLC property, not a contract invariant"
                )
            mapped = []
            sole_test: Dict[str, List[str]] = {}
            for item in model["invariants"]:
                invariant_count += 1
                name = item["name"]
                if name not in mapped:
                    mapped.append(name)
                if item.get("checked_by") == "tlc":
                    continue
                test_names = item.get("tests") or []
                if not test_names:
                    failures.append(f"FAIL invariant {name} in {cfg_display} lists no tests")
                    continue
                if len(test_names) == 1:
                    sole_test.setdefault(test_names[0], []).append(name)
                for test_name in test_names:
                    hit = tests.get(test_name)
                    if hit is None:
                        failures.append(
                            f"FAIL missing test: {test_name} for invariant {name} in {cfg_display}"
                        )
                        continue
                    if test_name in ran:
                        continue
                    ran.add(test_name)
                    problem = run_python_test(hit, test_name, loaded)
                    if problem:
                        failures.append(problem)
            for test_name, owners in sole_test.items():
                if len(owners) > 1:
                    print(f"note: {test_name} is the only test for {', '.join(owners)}")
            declared_set = set(declared)
            mapped_set = set(mapped)
            for name in declared:
                if name not in mapped_set:
                    failures.append(
                        f"FAIL missing mapping: {cfg_display} invariant {name} is not in the contract"
                    )
            for name in mapped:
                if name not in declared_set:
                    failures.append(
                        f"FAIL stale mapping: {cfg_display} lists {name} but that model does not check it"
                    )
            if want_tlc:
                if not tla_path.is_file():
                    failures.append(f"FAIL tlc: {cfg_display} missing module {spec['tla']}")
                else:
                    print(f"---- {spec_name} ({display(cfg_path, base)})")
                    problem = run_tlc(java, jar, tla_path, cfg_path)
                    if problem:
                        failures.append(f"FAIL tlc: {cfg_display} {problem}")
                    else:
                        print(f"ok tlc {cfg_display}")
    return failures, model_count, invariant_count, len(ran)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check a spec-to-test contract.")
    parser.add_argument(
        "--mapping",
        action="append",
        default=[],
        help="Path to a spec_coverage.yaml. Repeat to check several. Default: search the current directory.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Directory to search when --mapping is omitted.",
    )
    parser.add_argument(
        "--tlc",
        action="store_true",
        help="Run TLC on models whose mapping sets model_checker: tlc.",
    )
    parser.add_argument("--java", default=os.environ.get("JAVA", "java"))
    parser.add_argument(
        "--jar",
        default=os.environ.get("TLA2TOOLS_JAR", str(repo_root() / ".tools" / "tla2tools.jar")),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    if args.mapping:
        mappings = [Path(path).resolve() for path in args.mapping]
    else:
        mappings = discover(Path(args.root).resolve())
    if not mappings:
        sys.stderr.write("No spec_coverage.yaml found. Pass --mapping or add one.\n")
        return 2

    jar = Path(args.jar)
    if args.tlc:
        if not java_works(args.java):
            sys.stderr.write("Java 11 or newer is required. Install a JDK, or set JAVA=/path/to/java.\n")
            return 2
        try:
            ensure_jar(jar)
        except OSError as exc:
            sys.stderr.write(f"Could not download tla2tools.jar: {exc}\n")
            return 2

    all_failures: List[str] = []
    for mapping in mappings:
        if not mapping.is_file():
            sys.stderr.write(f"No such mapping: {mapping}\n")
            return 2
        try:
            data = load_mapping(mapping)
        except ContractError as exc:
            sys.stderr.write(f"{exc}\n")
            return 2
        failures, models, invariants, tests = check_mapping(
            mapping, data, args.tlc, args.java, jar
        )
        label = display(mapping, Path.cwd())
        if failures:
            all_failures.extend(failures)
            continue
        print(
            "contract ok: "
            f"{label}: {plural(models, 'model')}, {plural(invariants, 'invariant')}, {plural(tests, 'test')}"
        )

    if all_failures:
        for line in all_failures:
            print(line)
        print(f"contract failed: {len(all_failures)} problems")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
