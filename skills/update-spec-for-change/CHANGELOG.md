# Changelog

## 0.1.2 - 2026-11-06

- A new invariant can default to `test_` plus the snake-case name. An existing test keeps its name. Bookkeeping invariants can be `checked_by: tlc`.

## 0.1.1 - 2026-11-06

- Point at the surrounding chain: a first model, a state chart, and test-first implementation. The install list lives in `docs/chain.md`.

## 0.1.0 - 2026-11-06

- Initial skill. Propose invariant updates from a product change or a bug, place them in the module and the TLC config, and record safety invariants in the spec-to-test contract with a placeholder test name.
