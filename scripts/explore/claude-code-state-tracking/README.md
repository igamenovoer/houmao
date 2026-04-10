# Claude Code State Tracking Explore Harness

This harness validates the proposed simplified Claude turn-state model outside of `houmao-server`.

It has two complementary workflows:

1. batch scenario capture/replay for repeatable scripted cases, and
2. interactive watch for manual prompting with a live dashboard plus final replay-grade analysis.

Both workflows stay independent from `houmao-server`. They launch Claude through canonical preset-backed repository fixtures, record the tmux pane with `tools/terminal_record` in `passive` mode, derive content-first groundtruth from recorded pane snapshots plus runtime liveness observations, and replay the same observation stream through an independent ReactiveX tracker.

For the demo state model itself, and how it differs from and relates to the production `houmao-server` tracker that was later developed using this demo as a reference, see:

- `scripts/explore/claude-code-state-tracking/state-model.md`

## Main Workflow

Run one live scenario end to end:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py run \
  --scenario simple-success
```

Capture only:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py capture \
  --scenario interrupt-after-active
```

Replay and compare an existing capture root:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py replay \
  --run-root tmp/explore/claude-code-state-tracking/<run-id>
```

Compare already-generated timelines again:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py compare \
  --run-root tmp/explore/claude-code-state-tracking/<run-id>
```

## Interactive Watch

Start one interactive watch run:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py start \
  --json \
  --trace \
  --output-root tmp/explore/claude-code-state-tracking/interactive-watch/<run-id>
```

Inspect the live run and attach points:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py inspect \
  --json \
  --run-root tmp/explore/claude-code-state-tracking/interactive-watch/<run-id>
```

Stop the run and finalize the replay/comparison report:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py stop \
  --json \
  --run-root tmp/explore/claude-code-state-tracking/interactive-watch/<run-id>
```

The interactive watch:

- builds a fresh Claude brain home from `tests/fixtures/plain-agent-def/presets/interactive-watch-claude-default.yaml`
- writes that generated runtime under the run-local `runtime/` subtree
- launches the generated `launch.sh` directly in tmux
- forces Claude to start with `--dangerously-skip-permissions`
- still uses the tracked Claude setup bundle under `tests/fixtures/plain-agent-def/tools/claude/setups/default/` for baseline startup behavior
- does not use `houmao-server` routes or Houmao lifecycle CLIs for normal start/inspect/stop flow
- leaves a successful `start` run live for manual prompting until the operator later runs `stop`
- automatically reaps run-owned `cc-track-*` and `HMREC-*` tmux sessions if startup fails or is interrupted before the run reaches steady state
- preserves the run root and its logs/artifacts for debugging even when failed or interrupted startup cleanup reaps live tmux resources

The validated interactive run from 2026-03-20 is documented in:

- `scripts/explore/claude-code-state-tracking/reports/interactive-watch-live-20260320.md`

## Output Layout

Each run writes under:

```text
tmp/explore/claude-code-state-tracking/<timestamp>-<scenario-id>/
```

Important artifacts:

- `artifacts/capture_manifest.json`
- `artifacts/drive_events.ndjson`
- `artifacts/runtime_observations.ndjson`
- `runtime/homes/<home-id>/launch.sh`
- `runtime/manifests/<home-id>.yaml`
- `terminal_record/pane_snapshots.ndjson`
- `analysis/groundtruth_timeline.ndjson`
- `analysis/replay_timeline.ndjson`
- `analysis/replay_events.ndjson`
- `analysis/comparison.json`
- `analysis/comparison.md`
- `analysis/interactive_watch_report.md`

## Signal Discovery Workflow

When a new stable Claude signal is discovered during testing, formalize it instead of leaving it implicit in code:

```bash
pixi run python scripts/explore/claude-code-state-tracking/run.py signal-note-init \
  --slug claude-code-<signal-name> \
  --output-path openspec/changes/simplify-houmao-server-state-model/tui-signals/claude-code-<signal-name>.md
```

Then fill the generated note with:

- observed version context
- exact or structural matcher
- current-region / recency constraints
- non-match guidance
- concrete artifact references
