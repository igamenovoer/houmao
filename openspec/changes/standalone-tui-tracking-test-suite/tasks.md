## 1. Demo Pack Foundation

- [x] 1.1 Create `scripts/demo/shared-tui-tracking-demo-pack/` with operator-facing entrypoints for recorded validation and live watch workflows.
- [x] 1.2 Extract or add shared runtime-launch helpers for Claude and Codex fixture brains, including permissive default launch posture and tool-specific observed-version/process probing.
- [x] 1.3 Define stable run-root layouts and artifact path models for recorded runs and live watch runs under `tmp/demo/shared-tui-tracking-demo-pack/`.
- [x] 1.4 Add direct tmux/runtime probing helpers that feed the standalone tracker without `houmao-server` dependencies.
- [x] 1.5 Add unit coverage for path resolution, launch metadata, direct-probe behavior, and startup/cleanup behavior for workflow-owned tmux and recorder resources.

## 2. Recorded Validation Workflow

- [x] 2.1 Implement recorder-backed fixture capture that launches real tmux sessions, records with the terminal recorder, and persists replay-grade artifacts for the standalone tracker.
- [x] 2.2 Implement structured ground-truth authoring support that reads recorded samples directly, saves official tracked-state labels, validates sample coverage, and expands labels into `groundtruth_timeline.ndjson`.
- [x] 2.3 Implement replay and comparison flow that feeds recorded pane snapshots plus optional input/runtime evidence through the standalone tracker and emits replay/comparison artifacts.
- [x] 2.4 Implement final recorded-run Markdown reporting, including one summary report and separate per-issue Markdown documents inside the run output directory.
- [x] 2.5 Add automated tests for label expansion, replay-vs-ground-truth comparison, report generation, and failure behavior when authoritative capture or label coverage is missing.

## 3. Review Video Export

- [x] 3.1 Implement a terminal-style frame renderer that converts recorded pane snapshots plus ground-truth state into staged `1920x1080` review frames.
- [x] 3.2 Implement frame-timing expansion and `ffmpeg`-backed `.mp4` export using default `8 fps`, `libx264`, `yuv420p`, and persisted frame directories.
- [x] 3.3 Add tests for frame staging, encode command construction, and overlay rendering of visible ground-truth state changes.

## 4. Live Interactive Watch

- [x] 4.1 Implement a generic live watch start/inspect/stop workflow for Claude and Codex using fixture-backed runtime homes, recorder-backed observation, and separate tmux dashboard sessions.
- [x] 4.2 Implement the `rich` dashboard reducer loop that consumes recorder snapshots and runtime observations through the standalone shared tracker and persists `latest_state.json`, `state_samples.ndjson`, and `transitions.ndjson`.
- [x] 4.3 Finalize stopped live-watch runs with the same offline replay/comparison pipeline used by recorded validation, reusing the retained recorder evidence.
- [x] 4.4 Implement final live-watch Markdown reporting, including one summary report and separate per-issue Markdown documents inside the run output directory.
- [x] 4.5 Add unit coverage for live watch lifecycle, persisted state artifacts, report generation, and failure/interrupt cleanup paths for both supported tools.

## 5. Fixtures And Documentation

- [x] 5.1 Author and commit an initial recorded fixture corpus of at least four shared-tracker cases spanning Claude and Codex and covering success, interruption, and diagnostics-loss boundaries.
- [x] 5.2 Add or update fixture recipes/configs needed for Codex and Claude live watch runs under `tests/fixtures/agents/`.
- [x] 5.3 Document maintainer workflows for recording fixtures, labeling ground truth, generating review videos, reading the final Markdown reports, and triaging per-issue Markdown outputs.
