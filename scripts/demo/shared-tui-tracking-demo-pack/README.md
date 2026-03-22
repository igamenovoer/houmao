# Shared TUI Tracking Demo Pack

This demo pack validates the standalone tracked-TUI module directly from tmux and recorder evidence. It does not depend on `houmao-server`.

The package lives in [src/houmao/demo/shared_tui_tracking_demo_pack](/data1/huangzhe/code/houmao/src/houmao/demo/shared_tui_tracking_demo_pack) and the operator entrypoint is [run_demo.sh](/data1/huangzhe/code/houmao/scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh).

## Recorded Validation

Capture a real session with the recorder in active mode:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-capture \
  --scenario scripts/demo/shared-tui-tracking-demo-pack/scenarios/claude-explicit-success.json
```

Validate one captured fixture or committed fixture:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate \
  --fixture-root tests/fixtures/shared_tui_tracking/recorded/claude/claude_explicit_success
```

Validate the whole committed corpus:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate-corpus
```

Recorded validation writes under `tmp/demo/shared-tui-tracking-demo-pack/recorded/...` unless `--output-root` overrides it.

Each run produces:

- `analysis/summary_report.md`
- `analysis/groundtruth_timeline.ndjson`
- `analysis/replay_timeline.ndjson`
- `analysis/comparison.json`
- `issues/*.md` when problems are detected
- `review/frames/frame-*.png`
- `review/review.mp4` encoded with `ffmpeg`, `libx264`, `yuv420p`, and default `8 fps`

Ground truth comes from `labels.json`. The harness expands labels into a complete per-sample timeline and fails if sample coverage is incomplete or overlapping.

## Live Watch

Start a live watch dashboard for Claude:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool claude
```

Start a live watch dashboard for Codex:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool codex
```

Inspect the latest run:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh inspect --json
```

Stop the latest run:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh stop --json
```

Live watch writes under `tmp/demo/shared-tui-tracking-demo-pack/live/<tool>/<run-id>/`.

The normal launch posture is intentionally permissive:

- Claude always uses `--dangerously-skip-permissions`
- Codex uses the repo-managed runtime-home config with `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`

This avoids routine stalls on approval prompts during capture or observation.

## Fixture Maintenance

The committed fixture corpus is under [tests/fixtures/shared_tui_tracking/recorded](/data1/huangzhe/code/houmao/tests/fixtures/shared_tui_tracking/recorded).

Each case keeps:

- `fixture_manifest.json`
- `runtime_observations.ndjson`
- `recording/manifest.json`
- `recording/pane_snapshots.ndjson`
- `recording/input_events.ndjson` when explicit-input authority matters
- `recording/labels.json`

When authoring a new fixture:

1. Capture with `recorded-capture` against a real tmux session.
2. Read `recording/pane_snapshots.ndjson` directly and classify the official tracked fields in `recording/labels.json`.
3. Run `recorded-validate` to generate replay/comparison artifacts.
4. Check `analysis/summary_report.md` and any `issues/*.md` files.
5. Review `review/review.mp4` to confirm the labeled transitions visually match the session.

