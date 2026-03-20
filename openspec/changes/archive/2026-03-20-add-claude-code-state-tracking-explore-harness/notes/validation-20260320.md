# Validation 2026-03-20

## Scope

This note records the first implementation validation pass for the explore harness added under `scripts/explore/claude-code-state-tracking/`.

Observed Claude version during validation:

- `2.1.80 (Claude Code)`

Detector selection used during validation:

- closest-compatible Claude detector family: `2.1.x`

## Commands Run

Unit and static validation:

```bash
pixi run ruff check src/houmao/explore src/houmao/terminal_record/models.py scripts/explore/claude-code-state-tracking tests/unit/explore/test_claude_code_state_tracking.py
pixi run pytest tests/unit/explore/test_claude_code_state_tracking.py tests/unit/terminal_record/test_service.py
pixi run mypy src/houmao/explore/claude_code_state_tracking src/houmao/terminal_record/models.py
```

Real recording replay:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py replay \
  --run-root tmp/explore/claude-code-state-tracking/replay-gig3-20260320 \
  --recording-root tmp/terminal_record/gig-3-20260320T041035Z \
  --observed-version "2.1.80 (Claude Code)"
```

Live diagnostics and failure-path runs:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py run \
  --scenario startup-network-failure-injected \
  --output-root tmp/explore/claude-code-state-tracking/validate-startup-network-failure

pixi run python scripts/explore/claude-code-state-tracking/run.py run \
  --scenario process-killed-tmux-still-alive \
  --output-root tmp/explore/claude-code-state-tracking/validate-process-killed

pixi run python scripts/explore/claude-code-state-tracking/run.py run \
  --scenario target-disappeared-unavailable \
  --output-root tmp/explore/claude-code-state-tracking/validate-target-unavailable
```

## Results

### 1. Real Claude recording replay

Artifacts:

- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/replay-gig3-20260320/analysis/groundtruth_timeline.ndjson`
- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/replay-gig3-20260320/analysis/replay_timeline.ndjson`
- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/replay-gig3-20260320/analysis/comparison.json`

Result:

- `mismatch_count = 0`
- `transition_order_matches = true`

The replay for the existing `gig-3` Claude recording matched the future-aware groundtruth timeline exactly for this first-pass detector/reducer combination.

### 2. Startup injected-failure path

Artifacts:

- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/validate-startup-network-failure/artifacts/capture_manifest.json`
- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/validate-startup-network-failure/logs/launch-strace.log`
- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/validate-startup-network-failure/analysis/comparison.json`

Result:

- `mismatch_count = 0`
- `transition_order_matches = true`

Important limitation:

- the injected `connect:error=ECONNREFUSED:when=1` path did fire in `strace`
- the Claude surface did **not** turn into a stable visible known-failure frame in this run
- the capture stayed effectively in a ready posture after startup

So this validation pass proves the harness can run subprocess-owned fault injection and preserve replay-grade artifacts, but it does **not** yet prove a stable Claude-visible startup known-failure matcher for this wrapper/tool/version path.

### 3. Process killed while tmux survives

Artifacts:

- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/validate-process-killed/artifacts/runtime_observations.ndjson`
- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/validate-process-killed/analysis/comparison.json`

Result:

- `mismatch_count = 0`
- `transition_order_matches = true`

The runtime observations captured the intended `tui_down` path with the tmux target still observable.

### 4. Target disappeared / unavailable

Artifacts:

- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/validate-target-unavailable/artifacts/runtime_observations.ndjson`
- `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/validate-target-unavailable/analysis/comparison.json`

Result:

- `mismatch_count = 0`
- `transition_order_matches = true`

Important limitation:

- when the tmux target disappears entirely, the terminal recorder controller ends in `failed` because pane capture can no longer proceed
- the harness still preserves enough runtime observations to classify the diagnostics path as `unavailable`

This is acceptable for the current explore harness because the authoritative unavailable classification comes from the runtime diagnostics stream, not from recorder-controller success alone.

## New Signals

No new stable Claude TUI signal was discovered during this validation pass that warranted a new signal note beyond the existing maintained notes under `openspec/changes/simplify-houmao-server-state-model/tui-signals/`.

