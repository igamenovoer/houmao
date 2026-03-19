## 1. Standalone Demo Pack Setup

- [x] 1.1 Create the standalone demo-pack directory `scripts/demo/cao-dual-shadow-watch/` with `run_demo.sh`, `README.md`, `scripts/demo_driver.py`, and `scripts/watch_dashboard.py`.
- [x] 1.2 Add demo-local state/config models for the run root, shared CAO launcher config, per-agent session metadata, and monitor session metadata.
- [x] 1.3 Add or wire the tracked projection-oriented dummy-project fixture under `tests/fixtures/dummy-projects/` and implement provisioning that copies it into fresh Claude/Codex workdirs with standalone git initialization.

## 2. Driver Lifecycle

- [x] 2.1 Implement shared loopback CAO launcher setup for the demo run without calling other demo-pack scripts.
- [x] 2.2 Implement brain build and dual `start-session` orchestration for Claude and Codex using `cao_rest`.
- [x] 2.3 Force `--cao-parsing-mode shadow_only` for both started sessions and persist that posture in the demo state.
- [x] 2.4 Persist run-state artifacts and print attach commands for the Claude session, Codex session, and monitor session.
- [x] 2.5 Implement demo `inspect`/status output that surfaces both agent sessions plus monitor metadata from the persisted run state.
- [x] 2.6 Implement demo `stop` logic that stops both runtime sessions, terminates the monitor tmux session, and preserves logs and monitor artifacts.

## 3. Shadow Monitor Dashboard

- [x] 3.1 Implement the per-agent polling loop that fetches CAO `mode=full` output every 0.5 seconds and parses it with `ShadowParserStack`.
- [x] 3.2 Implement demo-local readiness-state derivation for `ready`, `waiting`, `blocked`, `failed`, `unknown`, and `stalled`.
- [x] 3.3 Implement demo-local completion tracking with ready-baseline capture, post-submit activity detection, stability timing, and stalled handling.
- [x] 3.4 Implement the `rich` dashboard layout that shows both agents side-by-side, including parser fields, lifecycle states, anomaly codes, and short projection tails.
- [x] 3.5 Persist `samples.ndjson` for every poll tick and `transitions.ndjson` for state changes only.
- [x] 3.6 Launch the dashboard in a dedicated tmux session and wire the driver to surface its attach command.

## 4. Validation and Documentation

- [x] 4.1 Add targeted tests for dummy-project provisioning, persisted run-state loading, and the standalone driver lifecycle helpers.
- [x] 4.2 Add targeted tests for the monitor state tracker covering blocked surfaces, completion stability, projection-change resets, and unknown-to-stalled transitions.
- [x] 4.3 Write the pack README with prerequisites, start/attach/stop workflow, `shadow_only` contract, dummy-project workdir posture, and manual state-validation exercises.
- [x] 4.4 Run `pixi run format && pixi run lint && pixi run typecheck` and fix any issues introduced by the change.
