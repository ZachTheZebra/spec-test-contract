# The chain

A product person does not have to write TLA+. They agree what the system is allowed to do, and they hand the team a packet a person or a coding agent can finish. Each step below is an existing skill. This repo owns the two steps that keep the rules and the tests tied together. The other skills stay in their own repos.

A person starts the product steps by name (`/grill-with-docs`, `/to-spec`, `/statechart`). The coverage check and the test loop can start on their own once the files exist. When the `.tla`, the `.cfg`, and the code already exist, start at the coverage check. Do not restart the interview.

## The path

| Step | Who starts it | Skill | What they leave behind |
|---|---|---|---|
| 1. Agree the words and the decisions | Product, with an engineer in the room | `grill-with-docs` | A glossary and short decision records |
| 2. Write the packet | Product, when the conversation is done | `to-spec`, then `to-tickets` | A spec and small tickets, each saying what blocks it |
| 3. Show the flow | Anyone, when the behavior is a sequence of states | `statechart` | A chart in the reader's words, and the shortest path to each broken rule |
| 4. Write the first model | The coding agent | `tla-check`, or `tlaplus-from-source` when the code already exists | A `.tla` module, a `.cfg`, and a TLC run |
| 5. Attach a test to each rule | The coding agent, on the first model and on every later change | `update-spec-for-change` | New or edited invariants, plus a placeholder test name in `spec_coverage.yaml` |
| 6. Build the behavior | The coding agent | `tdd`, usually from `implement` | Real tests at those names, written before the code |
| 7. Refuse the merge if a rule is bare | CI, or the agent before the PR | `check-invariant-coverage` | A pass, or a list of missing mappings, missing tests, and failures |

`grill-with-docs` calls `grilling` and `domain-modeling`. Install those with it. `to-spec` and `to-tickets` publish to the project's issue tracker. Run `setup-matt-pocock-skills` once in that repo first.

`tla-check` is the step when nobody has a model yet. `tlaplus-from-source` is the step when the code is already there and the model should be read off it. A later product change uses `update-spec-for-change` on that model. It does not start over.

## What product hands the team

One folder or one ticket is enough. It holds:

- The glossary and the decisions from step 1.
- The spec and the tickets from step 2.
- The chart from step 3, when the behavior moves through states.
- The `.tla` file, the `.cfg` file, and `spec_coverage.yaml` from steps 4 and 5.

The instruction that goes with the packet: implement the tickets with `tdd` at the test names in the contract, then run `check-invariant-coverage`. CI runs the same check.

On the velocity counter, that packet says which events count, which key an API call lands on, and which test protects each of those rules. The person who builds it does not have to rediscover the rules from a chat log.

## Install

```bash
npx skills add mattpocock/skills --skill grill-with-docs
npx skills add mattpocock/skills --skill grilling
npx skills add mattpocock/skills --skill domain-modeling
npx skills add mattpocock/skills --skill setup-matt-pocock-skills
npx skills add mattpocock/skills --skill to-spec
npx skills add mattpocock/skills --skill to-tickets
npx skills add mattpocock/skills --skill tdd
npx skills add mattpocock/skills --skill implement

npx skills add https://github.com/cursor/plugins/tree/main/pstack/skills/statechart

npx skills add younes-io/agent-skills --skill tla-check
npx skills add tlaplus/AgentSkills --skill tlaplus-from-source

npx skills add ZachTheZebra/spec-test-contract --skill update-spec-for-change
npx skills add ZachTheZebra/spec-test-contract --skill check-invariant-coverage
```

Sources:

- [mattpocock/skills](https://github.com/mattpocock/skills) for the interview, the spec, the tickets, and the test-first implementation.
- [statechart](https://github.com/cursor/plugins/tree/main/pstack/skills/statechart) by Lauren Tan, for a chart a reader can judge.
- [younes-io/agent-skills](https://github.com/younes-io/agent-skills) for `tla-check`, which writes a TLC-checked spec and reports a counterexample when it has one. A run that finds no error is a pass of that bounded model.
- [tlaplus/AgentSkills](https://github.com/tlaplus/AgentSkills) for a first model taken from existing source.

## Once the model exists

These are edits to a spec that is already underway. They are not a second path.

| Skill | Install | Use it when |
|---|---|---|
| `tlaplus-add-variable` | `npx skills add tlaplus/AgentSkills --skill tlaplus-add-variable` | A new fact has to be remembered, and every `UNCHANGED` and the type invariant must move with it |
| `tlaplus-split-action` | `npx skills add tlaplus/AgentSkills --skill tlaplus-split-action` | One step in the model is really two steps, such as a crash between two keys |
| `tla-proof` | `npx skills add younes-io/agent-skills --skill tla-proof` | The team wants a machine-checked proof with TLAPS. A model check is the usual stop. |

## One property that tests rarely reach

`create-formal-verification-skill` and `maintain-formal-verification-skill` live with [Pstack](https://github.com/cursor/plugins/tree/main/pstack). The first leaves a project-local check for a single high-stakes property. The second brings that check back in line when the code changes, and it keeps a code bug distinct from a stale model. Use them for one promise. The contract in this repo still lists every safety invariant the model checks.

```bash
npx skills add https://github.com/cursor/plugins/tree/main/pstack/skills/create-formal-verification-skill
npx skills add https://github.com/cursor/plugins/tree/main/pstack/skills/maintain-formal-verification-skill
```
