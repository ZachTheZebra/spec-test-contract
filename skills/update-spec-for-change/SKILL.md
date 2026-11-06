---
name: update-spec-for-change
description: "Examines an existing TLA+ spec against a product change or bug description and proposes new or modified invariants. Use when a requirement, feature request, or bug report arrives and the formal specification needs updating."
license: MIT
---

# Update a spec for a product change

A product change that never reaches the spec leaves the model describing yesterday's system. A bug that never becomes an invariant will be fixed in code and then written again. This skill turns a short change description into a concrete TLA+ proposal and a spec-to-test contract entry.

The contract file is the source of truth for how an invariant is recorded. When `docs/mapping-format.md` is in the workspace, follow it. The shape to append is:

```yaml
- name: InvariantName
  tests: [test_invariant_name]
```

Test names are `test_` plus the invariant name in snake case.

## What to read first

Read the module that owns the behavior, every `INVARIANT` and `PROPERTY` in its `.cfg` files, and the `spec_coverage.yaml` that points at those configs. Quote the formulas that already talk about the change. A new invariant is the wrong output when an existing one already states the rule.

Read [references/invariant-patterns.md](references/invariant-patterns.md) before writing a formula.

## Steps

1. Restate the change in one paragraph: who does what, and which state is forbidden or required. Use the names already in the module (keys, sets, actions). Ask for the failing trace when the description names a symptom and no state.
2. Say which current formulas cover the change, and which state they still allow.
3. Propose the smallest formula that makes the bad state illegal or the required state necessary. Include a fairness assumption only when the change is about something that eventually happens. Safety bugs do not need `SF_` or `WF_`.
4. Name the module location: after the operators the formula uses, and the exact `INVARIANT` or `PROPERTY` line to add to which `.cfg`. A liveness condition is a `PROPERTY` under `FairSpec`. It is not an `INVARIANT` line, and it is not a contract entry. Say that in the proposal.
5. Offer to run TLC. The command, from a checkout that has the checker, is:

   ```bash
   python scripts/check_coverage.py --mapping <spec_coverage.yaml> --tlc
   ```

   Run it when the user asks. Java 11+ is required. Set `JAVA` when `java` is not on `PATH`. Report a pass only when the output contains `No error has been found` or `contract ok`.
6. Update `spec_coverage.yaml` for each new or renamed safety invariant, with a placeholder test name. Leave the placeholder unimplemented. The coverage check is supposed to fail until a real test exists. Do not add `assert True` to turn the check green.

## Proposal shape

Use this shape so the formula, the config line, and the contract entry stay together:

```markdown
# Spec update

## Change
<one paragraph>

## Already specified
<formula names that already cover this, or "none">

## Proposal
### <InvariantName>
- Kind: safety invariant | action property | liveness property
- Formula:
  <TLA+ operator>
- Where: <module location> and `<cfg>` line `<INVARIANT or PROPERTY ...>`
- Why: <which newly illegal or newly required state this is>
- Fairness: none | <assumption, and the stuttering or loop it rules out>

## Contract
<yaml fragment for each safety invariant, or "no contract change" for a liveness property>

## TLC
<offer, or the command output>
```

## Keeping the model honest

- Change the formula so it states the new rule. Deleting an invariant, or weakening it until TLC is quiet, hides the regression.
- Keep a bug trace. If TLC finds a counterexample, the formula is wrong or the change is not what the trace shows. Do not edit constants (`MaxEvents`, `Retention`, and the rest) to push the counterexample out of the bound.
- One invariant, one obligation. A formula that says "the window is right and the route is right" is two rules. Split them so each can have its own test.
- Placeholder tests are unfinished work. Say that the contract stays red until the test exercises the implementation, not only a copied predicate.

## When this skill is the wrong tool

A request to see whether the current mapping still matches the configs is `check-invariant-coverage`. A request to implement the counter, the store, or the service is the product repo's work. Come back here when that implementation changes a rule the spec should state.
