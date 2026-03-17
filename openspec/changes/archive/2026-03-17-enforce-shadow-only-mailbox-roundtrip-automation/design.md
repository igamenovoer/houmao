## Context

The mailbox roundtrip tutorial pack already supports a generic `--cao-parsing-mode <cao_only|shadow_only>` surface and persists the selected mode in `demo_state.json` so later `roundtrip` and `stop` commands can reuse it. The current live tutorial-pack tests still hard-code `cao_only` for fresh starts, which means the automatic mailbox workflow is proving a mixed parsing strategy even though recent investigation showed that `cao_only` is the wrong path to trust for Claude mailbox turns. That investigation also confirmed that Codex now has a functional runtime shadow parser, so automatic mailbox coverage no longer needs a per-tool parsing split.

This proposal is intentionally about the automation contract, not about declaring every CAO-backed workflow in the repository shadow-only forever. We need the mailbox roundtrip automatic path to stop treating `cao_only` as a valid success route, keep both agents on the same transport/parsing model, and surface shadow-only failures directly so the resulting signals stay trustworthy.

## Goals / Non-Goals

**Goals:**

- Define one automatic CAO-backed mailbox roundtrip policy that uses `shadow_only` for both the Claude sender and the Codex receiver.
- Ensure the tutorial-pack automation persists and reuses `shadow_only` consistently across `start`, `roundtrip`, and `stop` for the same demo root.
- Treat Codex shadow parsing as the supported receiver path for mailbox roundtrip automation instead of dropping back to `cao_only`.
- Prevent automatic mailbox coverage from masking failures by retrying or reclassifying the same run under `cao_only`.

**Non-Goals:**

- Changing the general runtime contract that still supports both `cao_only` and `shadow_only` for CAO-backed sessions.
- Solving the underlying Claude mailbox-send stall or Claude shadow-parser fragility in this proposal.
- Removing all manual or debug-only uses of `--cao-parsing-mode cao_only` from unrelated CAO demo workflows.

## Decisions

### 1. Automatic mailbox roundtrip coverage will use one parsing policy: `shadow_only` for both participants

The automatic CAO-backed mailbox workflow should stop treating parsing mode as an experiment matrix. Both started sessions, and all subsequent mailbox commands driven through them, will use `shadow_only`. This keeps the sender and receiver on the same runtime-owned transport/gating model and ensures mailbox failures are observed on the path we actually want to stabilize.

Alternatives considered:

- Keep Claude on `shadow_only` but allow Codex to remain `cao_only`.
  Rejected because the repo runtime now has a functional Codex shadow parser and mixed-mode mailbox automation makes failures harder to compare and reason about.
- Continue allowing either mode as long as the run leaves mailbox artifacts.
  Rejected because that invites a "green by mode-switching" workflow where the automation result no longer proves the intended product path.

### 2. The tutorial-pack automation state will persist a resolved `shadow_only` mode and reuse it across the full workflow

Fresh automatic runs should resolve `shadow_only` at the beginning of the workflow and write that mode into the demo-owned state so `roundtrip` and `stop` reuse the same setting. This keeps stepwise automation aligned with one-shot automation and avoids accidental drift where the start phase and later mailbox operations run with different parsing assumptions.

The design should prefer one of two implementation shapes:

- make automatic callers pass `shadow_only` explicitly on fresh starts and persist that exact mode, or
- teach the tutorial-pack automation helpers to default the automatic CAO-backed path to `shadow_only` when no override is supplied.

Either way, the persisted automatic-workflow state becomes the source of truth for later steps.

Alternatives considered:

- Re-derive parsing mode independently on every command from ambient runtime defaults.
  Rejected because stepwise automation would become fragile if defaults change or if one command accidentally omits the intended mode.
- Keep persisting nullable mode and let later steps infer from live session behavior.
  Rejected because the automation contract should be explicit and inspectable in `demo_state.json`.

### 3. Automatic coverage will fail on `cao_only` requests or mixed-mode recovery instead of silently exploring them

For mailbox roundtrip automation, `cao_only` is now a disallowed coverage mode. If an automatic live workflow is explicitly configured to use `cao_only`, or tries to recover from a `shadow_only` failure by switching either participant to `cao_only`, that run should fail as an invalid automation configuration rather than being treated as a valid pass/fail mailbox result.

This enforcement belongs at the automation boundary: the tutorial-pack automatic helpers, live integration tests, and any scenario runner or owned automation wrapper that claims to satisfy the mailbox-roundtrip automation contract.

Alternatives considered:

- Leave the tooling permissive and rely only on maintainer discipline.
  Rejected because the current tests already demonstrate how easy it is for `cao_only` to creep back into the "automatic live" path.
- Remove `cao_only` from the tutorial-pack CLI entirely.
  Rejected because debug-oriented manual experiments may still need it, and this proposal is narrower than a repository-wide deprecation.

### 4. Manual/debug parsing-mode overrides remain outside the automatic coverage contract

The generic tutorial-pack CLI surface may continue to expose `--cao-parsing-mode` for debugging, but documentation and tests should clearly separate that from the automatic mailbox coverage path. A manual run that uses `cao_only` can still be useful diagnostically; it just must not count as satisfying the automated mailbox-roundtrip requirement.

Alternatives considered:

- Treat every invocation of `run_demo.sh` as automatic coverage and forbid `cao_only` globally.
  Rejected because it overreaches beyond the user request and collapses debugging flexibility into the product-facing automation contract.

## Risks / Trade-offs

- [The `shadow_only` path may fail more often than the old `cao_only` test path] -> Treat those failures as the intended signal and keep the existing fast hermetic coverage separate so maintainers still have a narrow regression layer.
- [Automation-only restrictions can drift from the generic tutorial-pack CLI] -> Document the distinction explicitly and encode it in live tests so the contract is visible in both code and maintainer docs.
- [Existing demo roots may still persist `cao_only` in old `demo_state.json` files] -> Keep automatic runs on fresh demo roots and let cleanup continue to honor existing persisted state when needed.
- [Codex shadow parser drift could block the mailbox workflow] -> Surface those failures directly as mailbox automation failures and avoid `cao_only` fallback so the product gap remains visible.

## Migration Plan

No user-facing migration is required because tutorial-pack demo roots are disposable and automatic runs already provision fresh output directories. Implementation should:

1. Update the live mailbox automation helpers and tests so fresh automatic CAO-backed runs resolve `shadow_only`.
2. Persist that mode in demo-owned state and reuse it in later automatic steps.
3. Mark `cao_only` as debug-only for this pack and fail fast if automatic live coverage is asked to use it.
4. Update maintainer documentation to reflect that mailbox roundtrip automatic coverage now assumes Codex shadow parsing is supported and that mixed-mode reruns do not satisfy the contract.

Rollback, if needed, is limited to relaxing the automation guard or test expectations; it does not require a data migration.

## Open Questions

- None for proposal-level design. The key policy choice is settled: automatic mailbox coverage uses `shadow_only` for both agents.
