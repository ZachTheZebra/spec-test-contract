# Spec Test Contract

When a product change or a bug arrives, the behavior rules have to move with it, and the build has to fail if a rule has no passing test. This repo packages that agreement. The rules are written in TLA+. A `spec_coverage.yaml` file names the unit test that protects each invariant. `scripts/check_coverage.py` reads the TLC configs, the mapping, and the tests, and returns a non-zero status when they disagree.

## Install the skills

```bash
npx skills add ZachTheZebra/spec-test-contract --skill update-spec-for-change
npx skills add ZachTheZebra/spec-test-contract --skill check-invariant-coverage
```

`update-spec-for-change` reads the current spec and proposes new or modified invariants for a requirement, feature request, or bug. `check-invariant-coverage` runs the checker and reports missing mappings, missing tests, failing tests, and TLC failures. The two skills can later be upstreamed to [tlaplus/AgentSkills](https://github.com/tlaplus/AgentSkills) on their own. The checker and the mapping file stay here, because they are the CI gate.

## Quick start

```bash
git clone https://github.com/ZachTheZebra/spec-test-contract
cd spec-test-contract
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_coverage.py --mapping examples/velocity-counter/spec_coverage.yaml
```

That command checks the worked example. The example is the VelocityCounter module from [osprey-velocity-counter](https://github.com/ZachTheZebra/osprey-velocity-counter): one event names two keys, a crash can fall between them, and an API event is stored on the api-client key rather than the user key. `examples/velocity-counter/models/small.cfg` lists the seven safety invariants. `examples/velocity-counter/spec_coverage.yaml` maps each one to a test in `examples/velocity-counter/tests/test_counter_rules.py`. Those tests restate the rules as Python predicates, which is enough to show the contract. A production repo points the same file at the tests that exercise the real implementation.

To run TLC as well, install Java 11 or newer and add `--tlc`. Set `JAVA` when the `java` binary is not on `PATH`.

```bash
python scripts/check_coverage.py --mapping examples/velocity-counter/spec_coverage.yaml --tlc
```

A green run prints one line:

```text
contract ok: examples/velocity-counter/spec_coverage.yaml: 1 model, 7 invariants, 7 tests
```

## End-to-end on a change

1. A bug or a feature arrives. The update skill reads `VelocityCounter.tla`, names the invariant that should change, and gives a formula, the place to put it, and a placeholder test name.
2. Add the operator to the module, an `INVARIANT` line to `models/small.cfg`, and the same name in `spec_coverage.yaml`.
3. Write the test. The placeholder name is supposed to fail the checker until the test exists.
4. Run the command above. CI runs it on every push and pull request (`.github/workflows/coverage.yml`).

The mapping rules, the failure lines, and the optional `tests_root` field are in [docs/mapping-format.md](docs/mapping-format.md).

## Layout

```text
spec-test-contract/
├── skills/
│   ├── update-spec-for-change/
│   └── check-invariant-coverage/
├── scripts/check_coverage.py
├── examples/velocity-counter/
├── docs/mapping-format.md
└── .github/workflows/coverage.yml
```

## License

MIT. See [LICENSE](LICENSE).
