# Spec Test Contract

When a product change or a bug arrives, the behavior rules have to move with it, and the build has to fail if a rule has no passing test. This repo packages that agreement. The rules are written in TLA+. A `spec_coverage.yaml` file names the unit test that protects each invariant. `scripts/check_coverage.py` reads the TLC configs, the mapping, and the tests, and returns a non-zero status when they disagree.

## Install the skills

```bash
npx skills add ZachTheZebra/spec-test-contract --skill update-spec-for-change
npx skills add ZachTheZebra/spec-test-contract --skill check-invariant-coverage
```

`update-spec-for-change` reads the current spec and proposes new or modified invariants for a requirement, feature request, or bug. `check-invariant-coverage` runs the checker and reports missing mappings, missing tests, failing tests, and TLC failures. The two skills can later be upstreamed to [tlaplus/AgentSkills](https://github.com/tlaplus/AgentSkills) on their own. The checker and the mapping file stay here, because they are the CI gate.

Those two skills assume a spec already exists. The rest of the path, from a product conversation to a packet a coding agent can build, uses skills that already live elsewhere. The order, the install commands, and the handoff are in [docs/chain.md](docs/chain.md).

## Quick start

```bash
git clone https://github.com/ZachTheZebra/spec-test-contract
cd spec-test-contract
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_coverage.py --mapping examples/velocity-counter/spec_coverage.yaml
```

That command checks the worked example. The tests call `examples/velocity-counter/counter.py`. `TypeOK` is left to TLC. The other invariants name those tests. The formulas stay in the `.tla` file.

To run TLC as well, install Java 11 or newer and add `--tlc`. Set `JAVA` when the `java` binary is not on `PATH`.

```bash
python scripts/check_coverage.py --mapping examples/velocity-counter/spec_coverage.yaml --tlc
```

A green run prints one line:

```text
contract ok: examples/velocity-counter/spec_coverage.yaml: 1 model, 7 invariants, 6 tests
```

## Use this on your repo

When the `.tla`, the `.cfg`, and the code already exist, start at the coverage check. Do not restart the interview.

From a checkout of this tool, run the script with the Python that has the project's dependencies installed, and point it at their file:

```bash
python scripts/check_coverage.py --mapping path/to/spec_coverage.yaml --tlc
```

The mapped functions run in that Python. A missing dependency fails the run the way `No module named 'redis'` does. Install those dependencies in that interpreter before the check.

The workflow in this repo only checks the example. A job in the other repo is the same command:

```yaml
- name: Check the spec-to-test contract
  run: python scripts/check_coverage.py --mapping path/to/spec_coverage.yaml --tlc
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
├── docs/chain.md
└── .github/workflows/coverage.yml
```

## License

MIT. See [LICENSE](LICENSE).
