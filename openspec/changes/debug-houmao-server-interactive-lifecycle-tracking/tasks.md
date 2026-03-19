## 1. Server Trace Instrumentation

- [x] 1.1 Add an opt-in tracking-debug sink and run-scoped output-root helper for `houmao-server` that writes structured NDJSON events only when the debug workflow is enabled
- [x] 1.2 Instrument `src/houmao/server/app.py` and `src/houmao/server/service.py` so terminal-input handling and prompt-submission recording emit correlated debug events
- [x] 1.3 Instrument `src/houmao/server/tui/tracking.py` so anchor arming/loss, per-cycle parsed-surface ingestion, reduction branching, operator-state construction, stability updates, and transition publication emit correlated debug events

## 2. Automatic Repro Workflow

- [x] 2.1 Add a maintainer-facing automatic debug runner that starts a fresh `houmao-server-dual-shadow-watch` demo run with tracking-debug enabled and writes all outputs under `tmp/houmao-server-tracking-debug/<timestamp>/`
- [x] 2.2 Let the runner tune tracking cadence and timing parameters for the debug run when needed, and persist the effective values alongside the captured artifacts
- [x] 2.3 Make the runner execute and capture a server-owned terminal-input prompt path, including inspect snapshots and pane captures before and after the prompt
- [x] 2.4 Make the runner execute and capture a direct tmux-input prompt path against the same demo substrate, including the same inspect snapshots and pane captures for side-by-side comparison
- [x] 2.5 Integrate optional libtmux-backed pane capture or terminal-recording artifacts as supplemental diagnostics when the server traces alone are insufficient to explain visible terminal behavior
- [x] 2.6 Generate a run summary that correlates the trace streams and explicitly reports whether prompt submission, turn-anchor arming, reduction progression, and transition publication occurred for each prompt path

## 3. Verification

- [x] 3.1 Add or update tests for the debug-gating and trace-emission behavior so normal runs stay silent and enabled runs emit the required event categories
- [x] 3.2 Run the automatic tracking-debug workflow against the known interactive lifecycle failure and preserve the resulting `tmp/` artifact path as verification evidence
- [x] 3.3 Review the produced summary and traces to identify the first failing stage in the interactive lifecycle path, then record that conclusion in the relevant issue or follow-up change notes

Verification artifact root:

- `tmp/houmao-server-tracking-debug/20260319-190736`
