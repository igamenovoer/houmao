# Claude Code State Tracking Explore Harness

This harness validates the proposed simplified Claude turn-state model outside of `houmao-server`.

It does four things:

1. launches `claude-yunwu` in tmux,
2. records the pane with `tools/terminal_record` in `passive` mode,
3. derives content-first groundtruth from recorded pane snapshots plus runtime liveness observations, and
4. replays the same observation stream through an independent ReactiveX tracker and compares the two timelines.

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

## Output Layout

Each run writes under:

```text
tmp/explore/claude-code-state-tracking/<timestamp>-<scenario-id>/
```

Important artifacts:

- `artifacts/capture_manifest.json`
- `artifacts/drive_events.ndjson`
- `artifacts/runtime_observations.ndjson`
- `terminal_record/pane_snapshots.ndjson`
- `analysis/groundtruth_timeline.ndjson`
- `analysis/replay_timeline.ndjson`
- `analysis/replay_events.ndjson`
- `analysis/comparison.json`
- `analysis/comparison.md`

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

