---
name: check-invariant-coverage
description: "Validates that every TLA+ invariant in the model configs is mapped to unit tests and that those tests exist. Use when checking the Spec-to-Test Contract before merging a change that touches the formal specification."
license: MIT
---

# Check invariant coverage

A spec change is ready to merge when every `INVARIANT` in the TLC configs is named in `spec_coverage.yaml` and every named test exists and passes. This skill runs that check and reports the gaps. It does not invent a new rule to make a red check green.

The mapping rules live in `docs/mapping-format.md` when this repo is the workspace. The checker's `FAIL` lines are the result. Quote them.

## Steps

1. Find every `spec_coverage.yaml` in the workspace, plus the `.tla` and `.cfg` files it names. Paths inside the yaml are relative to the yaml file.
2. Run the checker:

   ```bash
   python scripts/check_coverage.py --mapping <path-to-spec_coverage.yaml>
   ```

   With no `--mapping`, the script searches the working directory. Add `--tlc` when the user wants the model checked, not only the contract. Java 11+ is required for `--tlc`. Set `JAVA` when `java` is not on `PATH`.

   Search the workspace for `check_coverage.py` if `scripts/check_coverage.py` is absent. If there is no copy, stop and tell the user the contract cannot be enforced until the script from `ZachTheZebra/spec-test-contract` is added. Do not replace the script with a one-off grep.
3. Read the exit code. `0` is a pass. `1` is a contract or TLC failure. `2` means the file or the schema could not be read.
4. Report each `FAIL` line unchanged, then the smallest edit that clears it.

## How to read a failure

| Line | Edit |
|---|---|
| `FAIL missing mapping` | The config checks an invariant the contract does not name. Add that name and a real test, or remove the `INVARIANT` line if the rule was retired on purpose. Say which of the two the change is. |
| `FAIL stale mapping` | The contract names an invariant the config no longer checks. Remove the contract entry, or put the `INVARIANT` line back. |
| `FAIL missing test` | The test function is not defined under `tests_root` (default `tests`, next to the yaml). Add the function or correct the name. A placeholder that only does `assert True` does not protect the rule. |
| `FAIL test` | The test ran and raised. Fix the test or the behavior it calls. Do not delete the invariant. |
| `FAIL tlc` | TLC rejected the model. The tail of the TLC log is the evidence. Do not weaken the invariant to silence it. |
| `note: PROPERTY` | A liveness or action property is present. It is outside the contract. Mention it. Do not fail the contract for it. |
| `checked_by: tlc` | TLC owns that invariant. It still has to be listed. Do not ask for a test. A behavior the product has to show still needs one. |
| `note:` a shared test | One test is the only test for several invariants. Report the note. Do not fail the run for it. |

## Report shape

```markdown
# Spec-to-test contract

## Command
<exact command and exit code>

## Result
pass | fail

## Findings
<each FAIL or note line>

## Fixes
<one edit per finding>
```

On a pass, the findings section is the `contract ok` line and any `PROPERTY` notes. Do not propose new invariants on a pass.

## When this skill is the wrong tool

A request to change what the system should do, given a bug or a feature, is `update-spec-for-change`. Run this skill after that proposal has been written into the module, the config, and the mapping. A missing test is written with `tdd` against the implementation, then this check is run again.

The path from a product conversation to this check is `docs/chain.md` in [spec-test-contract](https://github.com/ZachTheZebra/spec-test-contract/blob/main/docs/chain.md).
