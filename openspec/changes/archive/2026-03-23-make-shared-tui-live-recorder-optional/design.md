## Context

The shared-TUI live-watch workflow currently starts terminal-recorder in passive mode every time a developer runs `scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start`, and the dashboard loop reduces recorder pane snapshots plus runtime observations into tracked state. This makes recorder lifecycle, recorder artifacts, and an extra recorder tmux session part of the default interactive path even when the operator only wants a quick live smoke test.

Recorded validation remains a different workflow with a stronger artifact contract: it intentionally drives recorder-backed capture and later replay/comparison. The requested change is only about live watch.

## Goals / Non-Goals

**Goals:**

- Make ordinary live-watch starts run without terminal-recorder by default.
- Keep the live dashboard and machine-readable live-state artifacts available for no-recorder runs.
- Preserve recorder-backed live replay/debug behavior when the operator explicitly opts in.
- Make the recorder choice visible in the demo-owned config, CLI, manifest, and docs.

**Non-Goals:**

- Changing recorded-capture or recorded-validation to stop using terminal-recorder.
- Guaranteeing offline replay/comparison for live-watch runs that did not opt into recorder capture.
- Changing tracked-state semantics, detector behavior, or review-video contracts.

## Decisions

### 1. Recorder enablement becomes an explicit live-watch debug control

The demo config will gain a live-watch recorder toggle with a checked-in default of disabled, and the operator-facing `start` path will gain an explicit opt-in override such as `--with-recorder`.

Rationale:

- Recorder capture is an evidence-production concern, not a required part of tool launch posture.
- Default-off matches the common “interactive test” use case while still allowing replay-debug runs on demand.

Alternatives considered:

- Keep recorder implicit and always on: rejected because it preserves the current surprise and overhead.
- Put recorder enablement under per-tool launch config only: rejected because recorder is a live-watch workflow concern rather than a property of Codex or Claude launch posture.

### 2. Live state reduction will support two pane-text evidence sources behind one observation shape

The live dashboard loop will continue to drive the shared tracker through `RecordedObservation` rows, but the source of pane text will depend on mode:

- recorder enabled: keep consuming recorder `pane_snapshots.ndjson`
- recorder disabled: capture the visible tmux pane directly on each live-watch poll and synthesize equivalent observation rows

Runtime liveness observations remain in both modes.

Rationale:

- The shared tracker already works on normalized observation objects and does not require recorder ownership.
- This keeps the reducer and downstream state-artifact pipeline shared instead of creating separate dashboard logic for recorder vs non-recorder runs.

Alternatives considered:

- Start a lightweight recorder even for “no-recorder” mode: rejected because it still launches recorder infrastructure by default.
- Maintain a separate ad hoc dashboard parser for non-recorder mode: rejected because it would fork the observation/reduction contract.

### 3. Recorder-owned artifacts and finalization become conditional

Live-watch manifests, inspect payloads, stop/finalization logic, and docs will treat recorder capture as optional. Recorder-enabled runs will retain the current replay-debug path. Recorder-disabled runs will still emit live-state artifacts and a final summary report, but they will not claim recorder roots, replay timelines, or comparison artifacts.

The persisted manifest will record whether recorder capture was enabled, and recorder-root fields will become optional.

Rationale:

- Operators need an unambiguous way to tell whether a run can be replayed offline.
- `inspect` and `stop` need to behave sensibly for both run types.

Alternatives considered:

- Always create an empty recorder root even when disabled: rejected because it falsely implies replay-grade evidence exists.

## Risks / Trade-offs

- [Risk] Direct tmux sampling may not align perfectly with recorder snapshot timing. → Mitigation: reuse the same configured sampling cadence and normalize direct captures into the same observation shape used by recorder-backed runs.
- [Risk] Existing inspect/stop code assumes recorder metadata always exists. → Mitigation: make recorder enablement explicit in the manifest and branch recorder status/finalization logic on that flag.
- [Risk] Developers may expect offline replay artifacts after every live-watch run. → Mitigation: document the new default clearly and make the recorder opt-in obvious in the CLI and config reference.

## Migration Plan

1. Add the recorder toggle to the demo-owned config contract with a checked-in default of disabled.
2. Update live-watch start, dashboard, inspect, and stop flows to support recorder-disabled runs.
3. Preserve backward read compatibility for existing live-watch manifests by treating older manifests with a populated recorder root and no explicit recorder flag as recorder-enabled.
4. Update docs and tests so the default operator story is “interactive watch without recorder,” with recorder explicitly presented as a replay-debug mode.

## Open Questions

None.
