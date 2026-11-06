# Spec-to-test contract

`spec_coverage.yaml` is the agreement between a TLA+ model and the unit tests that protect it. The coverage checker reads this file. CI fails when the agreement is incomplete.

## File

Put `spec_coverage.yaml` next to the spec it covers. One product repo can contain several of these files. The checker searches the tree for every `spec_coverage.yaml`, or you can pass one path.

Paths inside the file are relative to the file itself, not the shell's current directory.

## Schema

```yaml
model_checker: tlc
specs:
  - name: Service
    tla: Service.tla
    models:
      - config: models/small.cfg
        invariants:
          - name: TypeOK
            checked_by: tlc
          - name: RouteShape
            tests: [test_route_shape]
```

| Field | Meaning |
|---|---|
| `model_checker` | `tlc` when `--tlc` should run the Toolbox on these models. Any other value skips TLC for this file. |
| `specs[].name` | Short name used in checker output. |
| `specs[].tla` | Module file TLC checks. |
| `specs[].models[].config` | TLC config (`.cfg`). |
| `specs[].models[].invariants[].name` | Operator name. It must match an `INVARIANT` line in that config. |
| `specs[].models[].invariants[].tests` | One or more test function names. The list cannot be empty. Use this for a behavior the product has to show. |
| `specs[].models[].invariants[].checked_by` | `tlc`, and then there is no `tests` list. Use this for state the model has to remember. |
| `tests_root` | Optional. Directory of tests, relative to this file. Default is `tests`. |

Every `INVARIANT` still appears in the mapping, so a rule cannot vanish. `checked_by: tlc` is for state the model has to remember: a type invariant, or a variable that exists only in the spec. TLC checks it. It is not a stand-in for a behavior the product has to show. A behavior rule names tests.

A test name is a module-level Python function in a `.py` file under `tests_root`. The checker calls it with no arguments, so the function takes no required parameters. It does not import a test runner and it does not look inside unittest or pytest. A test that already exists keeps its name. The function in this file runs that test and raises if it fails:

```python
def test_route_shape():
    MyCase("test_human_and_ip").debug()
```

The function's only job is to run the test they already have and raise if it fails. Do not rename the suite so the names match the invariants. A new test can be named `test_` plus the snake-case invariant when nothing covers that rule yet.

## What must match

The set of `INVARIANT` names in each config and the set of `invariants[].name` entries for that config are the same set.

- An `INVARIANT` line with no mapping entry fails the check. The rule has vanished from the contract.
- A mapping entry whose name is not an `INVARIANT` in that config fails the check. The contract is stale.
- A mapped test that is not a function under `tests_root` fails the check.
- A mapped Python test that raises fails the check.
- One test that is the only test for several invariants prints a note. The run still passes. People can share a test on purpose. The note makes a thin mapping visible.

`INVARIANT` and `INVARIANTS` both count. A `\*` comment after the name is ignored. A line whose first token is not `INVARIANT` does not count, including a comment that mentions the word.

`PROPERTY` and `PROPERTIES` are TLC obligations. They are not part of this contract. The checker prints a note for each one and does not fail. Liveness still belongs in the model config. This file lists every safety invariant. A behavior rule names a test. A bookkeeping rule is `checked_by: tlc`.

## Checker

From a checkout of this repo:

```bash
pip install -r requirements.txt
python scripts/check_coverage.py --mapping examples/velocity-counter/spec_coverage.yaml
```

With no `--mapping`, the checker searches the current directory for every `spec_coverage.yaml`.

```bash
python scripts/check_coverage.py --tlc
```

`--tlc` runs TLC on each model whose file has `model_checker: tlc`. TLC needs Java 11 or newer. The jar is `TLA2TOOLS_JAR` if that variable is set, otherwise `.tools/tla2tools.jar` in this repo, downloaded from the TLA+ 1.7.4 release when it is missing. Set `JAVA` when `java` is not on `PATH`.

Exit `0` means the contract holds. Exit `1` means a mapping gap, a missing test, a failed test, or a TLC failure. Exit `2` means the file or the schema is unusable.

Failure lines:

```text
FAIL missing mapping: Service models/small.cfg invariant RouteShape is not in the contract
FAIL stale mapping: Service models/small.cfg lists OldRule but that model does not check it
FAIL missing test: test_route_shape for invariant RouteShape in Service models/small.cfg
FAIL test test_route_shape: assertion failed
FAIL tlc: Service models/small.cfg TLC rejected the model
```

A shared test prints a note and does not fail the run:

```text
note: test_window is the only test for WindowBoundary, ExpiredNotCounted
```

Success line:

```text
contract ok: path/to/spec_coverage.yaml: 1 model, 2 invariants, 1 test
```

## Worked example

`examples/velocity-counter/` is one module and a small counter. `models/small.cfg` checks seven safety invariants. `TypeOK` is `checked_by: tlc`. The other six name functions in `tests/test_counter_rules.py`, and those functions call `counter.py`. The formulas stay in the `.tla` file.

When a product change adds a rule:

1. Add the operator to the `.tla` module.
2. Add an `INVARIANT` line to the `.cfg` that should check it.
3. Add the same name under that model in `spec_coverage.yaml`. Name the existing test, or `checked_by: tlc` when the model has to remember the state.
4. Write a test only when the behavior has none yet. It calls the implementation.
5. Run the checker. It fails until steps 2, 3, and 4 agree.
