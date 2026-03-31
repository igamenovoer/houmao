## Context

The supported `single-agent-mail-wakeup` demo currently models Claude and Codex as separate output roots under `outputs/<tool>/`. That layout made early automation convenient, but it now fights the interactive/manual operator workflow because follow-up commands need either tool-specific output-root discovery or explicit `--demo-output-dir` arguments.

The deeper constraint is not only path naming. The demo currently treats the entire output root as disposable, but project-easy specialists are persisted in overlay-backed state under the redirected project overlay. In practice, the reusable specialist lives in:

- `overlay/catalog.sqlite`
- `overlay/content/`
- `overlay/easy/`
- `overlay/agents/`

By contrast, copied project content, mailbox conversations, runtime sessions, logs, and evidence are run-local and safe to reset. The design therefore needs a stable split between persistent demo configuration and ephemeral run state.

## Goals / Non-Goals

**Goals:**
- Replace the per-tool `outputs/<tool>/` layout with one canonical `outputs/` root for the demo.
- Let follow-up commands resolve the active run from canonical persisted state without requiring `--demo-output-dir` during normal usage.
- Preserve overlay-backed specialist/auth/setup state across runs so repeated demo launches do not recreate specialists unnecessarily.
- Reset mailbox, copied project, runtime, log, delivery, and evidence state on each fresh `start`.
- Keep `claude` and `codex` as supported tool selections while making the selected tool a property of persisted demo state rather than directory layout.

**Non-Goals:**
- Reuse a previously launched managed-agent instance or tmux session across runs.
- Preserve previous run mailbox content, deliveries, evidence, or copied project artifacts.
- Support concurrent Claude and Codex live runs for this demo from one shared root.
- Generalize this state model to every other demo pack in `scripts/demo/`.

## Decisions

### Use one canonical demo output root

The demo will use:

```text
scripts/demo/single-agent-mail-wakeup/outputs/
```

as the single managed state root for both supported tools. The selected tool will be stored in persisted demo state and surfaced in command output, but it will no longer be encoded in the output directory name.

This is better than keeping `outputs/<tool>/` because the interactive surface is inherently single-run oriented. Commands such as `attach`, `watch-gateway`, `send`, and `notifier ...` become simpler when they always resolve `outputs/control/demo_state.json` instead of choosing among multiple tool-specific roots.

Alternative considered:
- Keep per-tool roots and improve auto-discovery. Rejected because it still leaves ambiguous state selection whenever both lanes have been started before, and it keeps the operator-facing contract heavier than necessary.

### Preserve overlay-backed specialist state but reset ephemeral run state

The demo will treat `overlay/` as partially persistent:

- preserved across runs:
  - `overlay/houmao-config.toml`
  - `overlay/catalog.sqlite`
  - `overlay/content/`
  - `overlay/easy/`
  - `overlay/agents/`
- reset on each new run:
  - `overlay/mailbox/`

The demo will also reset:

- `control/`
- `logs/`
- `runtime/`
- `registry/`
- `jobs/`
- `deliveries/`
- `evidence/`
- `project/`

This preserves the project-easy specialist, generated role projection, auth bundle, and related overlay-owned configuration while still guaranteeing a fresh mailbox and runtime for each run.

Alternative considered:
- Delete all of `overlay/` on each run. Rejected because it forces specialist recreation and auth reimport every time, which is exactly the friction this change intends to remove.

### Follow-up commands will resolve a single active run from canonical state

Normal stepwise commands will target the single canonical persisted demo state at `outputs/control/demo_state.json`. They will no longer require `--demo-output-dir` in the supported operator flow.

The demo may retain `--demo-output-dir` only as an internal/testing override if needed, but the documented operator contract should treat the canonical root as the default and expected target.

Alternative considered:
- Infer the tool from running tmux sessions or registry state alone. Rejected because persisted demo state is the authoritative contract already used by the pack, and tmux-only inference is weaker and less deterministic.

### Tool selection remains explicit at start time only

`start --tool claude|codex` remains the operator entry point for choosing the lane. After that, follow-up commands operate on the selected tool recorded in persisted state until the run is stopped and replaced by a new `start`.

This keeps the demo simple:

```text
one canonical outputs/
one active run
one selected tool in demo_state.json
```

Alternative considered:
- Support concurrent Claude and Codex sessions within one shared root. Rejected because it reintroduces the ambiguity this change is removing and does not match the interactive teaching intent of the pack.

### Matrix behavior will no longer depend on per-tool live roots

`matrix` will need to run the supported lanes sequentially against the canonical output root, resetting ephemeral state between runs while preserving reusable overlay-backed specialist state as appropriate for the selected tool.

This keeps the demo’s multi-tool smoke coverage while aligning it with the new single-root contract.

## Risks / Trade-offs

- [Persistent overlay accumulates tool-specific content] → Preserve only the overlay subtrees that define specialists and auth/setup content; explicitly reset mailbox state and all non-overlay run artifacts each run.
- [Switching tools may leave conflicting specialist names or auth bundles] → Use deterministic per-tool specialist naming and make `start --tool ...` responsible for selecting or refreshing the matching specialist content under the shared overlay.
- [Existing tests and docs assume `outputs/<tool>/`] → Update README, expected report shape, and focused unit tests together with the path-resolution logic.
- [Matrix semantics become less parallel-friendly] → Treat `matrix` as a sequential smoke harness rather than a concurrent dual-root workflow.

## Migration Plan

1. Change the demo layout helpers and state discovery to target one canonical `outputs/` root.
2. Split reprovision behavior into preserved overlay-backed specialist state vs resettable ephemeral state.
3. Update stepwise and automatic command flows, README examples, and follow-up command output to stop teaching `--demo-output-dir` for normal usage.
4. Update tests and expected report fixtures to match the new single-root layout.
5. Verify both supported lanes still run successfully from the simplified contract.

Rollback is straightforward: restore the previous `outputs/<tool>/` path resolution and full-root reprovision behavior if the shared-root model proves too ambiguous in practice.

## Open Questions

- Whether `--demo-output-dir` should remain as an undocumented/testing-only override or be removed entirely from the public CLI surface.
- Whether the demo should keep stable per-tool specialist names under the shared overlay or continue regenerating tool-specific suffixed specialists on each run while preserving the supporting overlay content.
