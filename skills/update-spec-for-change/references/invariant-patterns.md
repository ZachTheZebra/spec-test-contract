# Invariant patterns

Use these when writing a proposal. They are shapes, not a library to paste.

## Safety state invariant

A state predicate. TLC checks it in every reachable state. Use it when the change says some data must never look a certain way: a count is negative, an event sits on a key it was not routed to, a stored tick is missing from the "ever recorded" set.

```tla
NoNegativeCounts ==
  \A k \in Keys : count[k] >= 0
```

Place the operator after the operators it mentions, and add `INVARIANT NoNegativeCounts` to the safety config. Add the same name to `spec_coverage.yaml`.

## Action property

A step that must preserve something. TLC checks `[][Action]_vars` as a temporal formula, usually declared with `PROPERTY`, not `INVARIANT`. Use it when the change is about what one step may do: cleanup may remove an expired tick and must leave a live tick in place; one step writes at most one key.

```tla
ActivePreserved ==
  [][\A k \in Keys :
       \A e \in ticks[k] :
         (ts(e) > now - Retention) => e \in ticks'[k]]_vars
```

The next-state variable is primed (`ticks'[k]`). Forgetting the prime makes the formula talk about one state twice. An action property is not a contract invariant. Say so in the proposal. If the same rule has a unit-testable core (the predicate "this timestamp is still inside the window"), also propose that predicate as an `INVARIANT` and map the test to it.

## Liveness

Use a liveness property when the change is about completion: a delivered event eventually sits on every key in its route, a retry eventually finishes the key a crash skipped. Fairness is part of the claim. Weak fairness (`WF_vars`) loses to a loop that takes the action sometimes and starves one event. Strong fairness (`SF_vars`) on the specific action (`Deliver(e)`, `ApplyEventKey(e, k)`) is the usual fix, and it still allows finitely many crashes when `Crash` itself is not fair.

```tla
FairSpec ==
  /\ Spec
  /\ \A e \in EventIds : SF_vars(Deliver(e))

Completion ==
  <>(\A e \in EventIds : \A k \in Route(e) : e \in recorded[k])
```

Check liveness in its own config: `SPECIFICATION FairSpec` and `PROPERTY Completion`. Do not put `Completion` in the safety config, and do not add it under `invariants:` in the contract. A finite model-checker run cannot wait for "eventually."

## Where the lines go

| Change | Module | Config | Contract |
|---|---|---|---|
| A state that must never happen | `Name == <state predicate>` | `INVARIANT Name` in the safety cfg | `name: Name` plus a test |
| A step that must preserve a fact | `Name == [][<action>]_vars` | `PROPERTY Name` | no invariant entry; optional safety predicate for the testable core |
| Something that eventually happens | property under `FairSpec` | `PROPERTY Name` in the liveness cfg | no invariant entry |

## Bounds

Constants such as `MaxEvents`, `Retention`, and `MaxNow` define the finite model. A proposal that raises them to avoid a counterexample is a different model, not a fix. Mention a bound only when the new rule is invisible at the current bound (the bug needs three events and the model allows two).

## Names

Match the style of the module you are editing. Prefer a word for the obligation (`ExpiredNotCounted`, `OnlyRouted`) over a word for the ticket (`Bug1432`, `NewCheck`). The test name follows: `test_expired_not_counted`.
