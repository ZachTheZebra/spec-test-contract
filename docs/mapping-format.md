# Spec-to-test contract

`spec_coverage.yaml` is the agreement between a TLA+ model and the unit tests that protect it. The coverage checker reads this file. CI fails when the agreement is incomplete.

## File

Put `spec_coverage.yaml` next to the spec it covers. One product repo can contain several of these files. The checker searches the tree for every `spec_coverage.yaml`, or you can pass one path.

Paths inside the file are relative to the file itself, not the shell's current directory.

## Schema

```yaml
model_checker: tlc
specs:
  - name: VelocityCounter
    tla: VelocityCounter.tla
    models:
      - config: models/small.cfg
        invariants:
          - name: TypeOK
            tests: [test_type_ok]
          - name: WindowBoundary
            tests: [test_window_boundary]
```

| Field | Meaning |
|---|---|
| `model_checker` | `tlc` when `--tlc` should run the Toolbox on these models. Any other value skips TLC for this file. |
| `specs[].name` | Short name used in checker output. |
| `specs[].tla` | Module file TLC checks. |
| `specs[].models[].config` | TLC config (`.cfg`). |
| `specs[].models[].invariants[].name` | Operator name. It must match an `INVARIANT` line in that config. |
| `specs[].models[].invariants[].tests` | One or more test function names. The list cannot be empty. |
| `tests_root` | Optional. Directory of tests, relative to this file. Default is `tests`. |

A test name is a module-level Python function in a `.py` file under `tests_root`. The checker calls it with no arguments, so the function takes no required parameters. Name it `test_` plus the invariant name in snake case: `WindowBoundary` becomes `test_window_boundary`.

## What must match

The set of `INVARIANT` names in each config and the set of `invariants[].name` entries for that config are the same set.

- An `INVARIANT` line with no mapping entry fails the check. The model is checking a rule no test owns.
- A mapping entry whose name is not an `INVARIANT` in that config fails the check. The contract is stale.
- A mapped test that is not a function under `tests_root` fails the check.
- A mapped Python test that raises fails the check.

`INVARIANT` and `INVARIANTS` both count. A `\*` comment after the name is ignored. A line whose first token is not `INVARIANT` does not count, including a comment that mentions the word.

`PROPERTY` and `PROPERTIES` are TLC obligations. They are not part of this contract. The checker prints a note for each one and does not fail. Liveness still belongs in the model config. This file tracks safety invariants that a unit test can fail in one run.

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
FAIL missing mapping: VelocityCounter models/small.cfg invariant RouteShape is not in the contract
FAIL stale mapping: VelocityCounter models/small.cfg lists OldRule but that model does not check it
FAIL missing test: test_route_shape for invariant RouteShape in VelocityCounter models/small.cfg
FAIL test test_window_boundary: expected the boundary event to sit in the window
FAIL tlc: VelocityCounter models/small.cfg TLC rejected the model
```

Success line:

```text
contract ok: examples/velocity-counter/spec_coverage.yaml: 1 model, 7 invariants, 7 tests
```

## Worked example

`examples/velocity-counter/` carries the VelocityCounter module from [osprey-velocity-counter](https://github.com/ZachTheZebra/osprey-velocity-counter). `models/small.cfg` checks the seven safety invariants at `MaxEvents=2`, `Retention=2`, `MaxNow=4`. `tests/test_counter_rules.py` restates those rules as Python predicates and is the contract for this example.

When a product change adds a rule:

1. Add the operator to the `.tla` module.
2. Add an `INVARIANT` line to the `.cfg` that should check it.
3. Add the same name under that model in `spec_coverage.yaml`, with a new test name.
4. Write the test.
5. Run the checker. It fails until steps 2, 3, and 4 agree.
