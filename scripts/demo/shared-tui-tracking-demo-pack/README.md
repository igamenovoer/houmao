# Shared TUI Tracking Demo Pack

This demo pack validates the standalone tracked-TUI module directly from tmux observation, with optional recorder evidence when replay debugging is needed. It does not depend on `houmao-server`.

The package lives in [src/houmao/demo/shared_tui_tracking_demo_pack](/data1/huangzhe/code/houmao/src/houmao/demo/shared_tui_tracking_demo_pack) and the operator entrypoint is [run_demo.sh](/data1/huangzhe/code/houmao/scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh).

For the developer-facing contract on how human ground truth is compared against tracker output, read [GT_STATE_COMPARISON_CONTRACT.md](/data1/huangzhe/code/houmao/scripts/demo/shared-tui-tracking-demo-pack/GT_STATE_COMPARISON_CONTRACT.md).

The demo-owned configuration surface is [demo-config.toml](/data1/huangzhe/code/houmao/scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml). By default it aligns tmux capture cadence with the Houmao server baseline of `0.2s`, and review-video cadence matches the underlying capture cadence unless you explicitly override it. The checked-in demo now treats `2 Hz` capture frequency, meaning `sample_interval_seconds <= 0.5`, as the lower robustness floor for tracked public state.

The tracked launch assets live under [inputs/agents/](/data1/huangzhe/code/houmao/scripts/demo/shared-tui-tracking-demo-pack/inputs/agents). Each live-watch or recorded-capture run copies that tree into `workdir/.houmao/agents/`, then projects one selected-tool `auth/default` alias from the host-local fixture bundles under `tests/fixtures/agents/tools/<tool>/auth/`.

For a section-by-section explanation of the config, merge order, sweeps, and alternate config-file usage, read [CONFIG_REFERENCE.md](/data1/huangzhe/code/houmao/scripts/demo/shared-tui-tracking-demo-pack/CONFIG_REFERENCE.md).

## Recorded Validation

Capture a real session with the recorder in active mode:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-capture \
  --scenario scripts/demo/shared-tui-tracking-demo-pack/scenarios/claude-explicit-success.json \
  --profile canonical_fixture
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

If the configured committed fixture root is missing or has no fixture manifests, `recorded-validate-corpus` now fails during preflight with the concrete path instead of starting replay and failing later.

To emit the replay-path debug logs from `houmao.shared_tui_tracking` and the demo pack itself during investigation, set `HOUMAO_SHARED_TUI_TRACKING_LOG_LEVEL` to a normal Python logging level before running the command:

```bash
HOUMAO_SHARED_TUI_TRACKING_LOG_LEVEL=DEBUG \
  scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate-corpus --skip-video
```

Recorded validation writes under `tmp/demo/shared-tui-tracking-demo-pack/recorded/...` unless `--output-root` overrides it.

Each recorded-capture run now persists a run-local `session_ownership.json` before tmux launch and tags demo-owned tmux sessions with matching recovery pointers in tmux session environment. If a capture dies after tmux startup but before `capture_manifest.json` is written, the run is still recoverable through `cleanup`.

Each run produces:

- `analysis/summary_report.md`
- `analysis/groundtruth_timeline.ndjson`
- `analysis/replay_timeline.ndjson`
- `analysis/comparison.json`
- `artifacts/resolved_demo_config.json`
- `issues/*.md` when problems are detected
- `review/frames/frame-*.png`
- `review/review.mp4` encoded with `ffmpeg`, `libx264`, `yuv420p`, and the same cadence as capture by default

Ground truth comes from `labels.json`. The harness expands labels into a complete per-sample timeline and fails if sample coverage is incomplete or overlapping.

To inspect or override the demo-owned defaults explicitly:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate \
  --demo-config scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml \
  --profile fast_local \
  --fixture-root tests/fixtures/shared_tui_tracking/recorded/claude/claude_explicit_success
```

To switch to a different config file entirely, point the command at another TOML:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate \
  --demo-config /path/to/alternate-demo-config.toml \
  --fixture-root tests/fixtures/shared_tui_tracking/recorded/claude/claude_explicit_success
```

To test tracker robustness against sparser effective tmux capture cadences on one recorded fixture:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-sweep \
  --fixture-root tests/fixtures/shared_tui_tracking/recorded/claude/claude_explicit_success \
  --sweep capture_frequency
```

The sweep command writes under `tmp/demo/shared-tui-tracking-demo-pack/sweeps/...` unless `--output-root` overrides it. Sweep variants are evaluated against transition contracts from `demo-config.toml`, not against the canonical per-sample GT timeline.

The checked-in `capture_frequency` sweep is meant to validate robustness only down to that `2 Hz` floor. If you want to probe slower cadences, use an alternate config and treat the result as exploratory rather than part of the demo's default robustness claim.

## Live Watch

Start a live watch dashboard for Claude:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool claude
```

Start a live watch dashboard for Codex:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool codex
```

Enable recorder-backed live capture only when you want replay-debug artifacts from the same run:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool claude --with-recorder
```

Use an alternate config file for live watch when you want different path roots, capture cadence, or sweep definitions:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start \
  --tool claude \
  --demo-config /path/to/alternate-demo-config.toml
```

Inspect the latest run:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh inspect --json
```

Stop the latest run:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh stop --json
```

Forcefully reap stale demo-owned tmux sessions for the latest recoverable run:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh cleanup --json
```

Target one specific run root when you want recovery without relying on the latest-run heuristic:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh cleanup \
  --run-root tmp/demo/shared-tui-tracking-demo-pack/live/claude/20260322T000000 \
  --json
```

If you started the run with a config that changes `live_root` or `recorded_root`, use the same `--demo-config` again for `inspect`, `stop`, and `cleanup` unless you pass `--run-root` explicitly:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh inspect \
  --demo-config /path/to/alternate-demo-config.toml \
  --json

scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh stop \
  --demo-config /path/to/alternate-demo-config.toml \
  --json

scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh cleanup \
  --demo-config /path/to/alternate-demo-config.toml \
  --json
```

Live watch writes under `tmp/demo/shared-tui-tracking-demo-pack/live/<tool>/<run-id>/`.

The normal launch posture is intentionally permissive, and the default live-watch path is intentionally lightweight:

- The checked-in Claude and Codex interactive-watch recipes request `launch_policy.operator_prompt_mode: unattended`
- Those checked-in recipes live under `inputs/agents/roles/interactive-watch/presets/<tool>/default.yaml` and keep the tracked auth contract at `auth: default`
- Live watch defaults to `live_watch_recorder_enabled = false`, so an ordinary interactive test does not start terminal-recorder
- Use `--with-recorder` or a config/profile override only when you want retained replay-debug artifacts from that run

This avoids routine approval stalls during observation without paying recorder overhead on every smoke test.

Each live run also persists `artifacts/resolved_demo_config.json` so later inspection can see which launch, evidence, semantic, and presentation defaults were active.

Each live or recorded run also keeps a run-local `session_ownership.json` with the demo-owned tool, dashboard, and recorder resources known for that run. `stop` remains the graceful live-watch finalization path that writes replay and report artifacts. `cleanup` is the forceful recovery path for stale tmux sessions and does not claim finalized analysis output.

## Real Fixture Authoring Plan

The committed fixture corpus is under [tests/fixtures/shared_tui_tracking/recorded](/data1/huangzhe/code/houmao/tests/fixtures/shared_tui_tracking/recorded).

Temporary authoring runs should go under `tmp/demo/shared-tui-tracking-demo-pack/authoring/<tool>/<case>/...` by passing `--output-root` to `recorded-capture` and `recorded-validate`. Do not capture directly into the committed fixture tree.

### First-Wave Case Matrix

The first real authoring wave is intentionally narrow and uses concrete prompts or explicit operator actions:

- Claude `claude_explicit_success`: send `Reply with the single word READY and stop.`
- Claude `claude_interrupted_after_active`: send `Search this repository for files related to tmux and prepare a grouped summary. Think carefully before answering.`, wait for the active surface, run the scenario-owned `interrupt_turn` intent, then wait for the interrupted-ready posture
- Claude `claude_double_interrupt_then_close`: send one long-running prompt, wait for the active surface, run the scenario-owned `interrupt_turn` intent, send a second long-running prompt, interrupt again, then run the scenario-owned `close_tool` intent
- Claude `claude_success_interrupt_success_complex`: send `Return exactly READY and nothing else. Do not use tools.`, hold the first settled success, keep one visible ready-draft hold before each long submit, keep one visible active-draft hold during each long-running turn, interrupt twice, then finish with `Return exactly RECOVERED and nothing else. Do not use tools.`
- Claude `claude_slash_menu_recovery`: wait for ready, type `/` without submit, hold the overlay, then dismiss with `Escape`
- Claude `claude_tui_down_after_active`: send `Search this repository for files related to tmux and prepare a grouped summary. Think carefully before answering.`, wait for the active surface, then kill the tracked tmux session
- Codex `codex_explicit_success`: send `Reply with the single word READY and stop.`
- Codex `codex_interrupted_after_active`: send `Search this repository for files related to tmux and prepare a grouped summary. Think carefully before answering.`, wait for the active surface, run the scenario-owned `interrupt_turn` intent, then wait for the interrupted-ready posture
- Codex `codex_double_interrupt_then_close`: send one long-running prompt, wait for the active surface, run the scenario-owned `interrupt_turn` intent, send a second long-running prompt, interrupt again, then run the scenario-owned `close_tool` intent
- Codex `codex_success_interrupt_success_complex`: mirror the Claude complex lifecycle with one initial short success, two long interrupted turns with visible ready-draft and active-draft holds, then one final short recovered success
- Codex `codex_tui_down_after_active`: send `Search this repository for files related to tmux and prepare a grouped summary. Think carefully before answering.`, wait for the active surface, then kill the tracked tmux session

Each case targets one critical transition family:

- explicit success: ready -> active -> ready/success
- interrupted after active: active -> interrupted -> ready
- repeated intentional interruption with close: ready -> active -> interrupted -> active -> interrupted -> diagnostics down
- success-interrupt-success complex: ready/success -> active -> interrupted -> active -> interrupted -> ready/success, while preserving ready-draft and active-draft spans in the strict ground-truth labels
- slash-menu ambiguity: ready -> ambiguous overlay -> ready
- diagnostics loss: active -> `tui_down`

### Notes From Real Authoring

- In active recorder-driven Codex captures, submit the prompt as two managed events, not one collapsed `text<[Enter]>` sequence. The real TUI can leave the text staged without submitting when the `Enter` lands too tightly behind the literal text.
- Promote only `managed_send_keys` rows into committed `recording/input_events.ndjson`. Recorder handshake noise and other `asciinema_input` rows are useful during capture debugging but should not become replay authority in the canonical fixture tree.
- The interruption scenarios now use semantic `interrupt_turn` plus an explicit wait for the interrupted-ready posture before the next prompt is sent. That keeps repeated-turn authoring honest for both Claude and Codex instead of advancing on a transient prompt redraw.
- The capture driver waits and pattern checks inspect the visible pane surface rather than tmux scrollback. This avoids false positives from stale `esc to interrupt` rows or prior prompt text that are no longer on screen.
- Codex interrupted banners can wrap across multiple terminal lines. The Codex detector normalizes wrapped whitespace before judging interrupted-ready posture so the canonical fixtures remain valid across pane widths.
- For Claude complex authoring, `wait_for_active` must key off the latest-turn spinner line rather than the footer summary. Real active samples rotate symbols such as `✢`, `✻`, `✽`, `✶`, `·`, and `*`, while the footer can stay visually similar across ready and active spans.
- For the maintained complex fixtures, keep the prompt region visible during both active-draft holds. The checked-in scenarios use `1.2s` holds for ready-draft and active-draft spans, `1.0s` for the final ready-draft hold, and `1.4s` for the settled-success holds so the `0.2s` capture cadence and the default sweep cadence can sample each span cleanly.
- Claude interrupted-ready authoring should watch for the explicit line `⎿ Interrupted · What should Claude do instead?` and treat the first visible occurrence as sufficient authority before continuing to the next prompt.

### Authoring Workflow

When authoring or replacing a canonical fixture:

1. Scout the live surface first when prompt timing is uncertain:

```bash
bash scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool claude
bash scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool codex
```

2. Capture the real session into a temporary authoring root:

```bash
bash scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-capture \
  --scenario scripts/demo/shared-tui-tracking-demo-pack/scenarios/claude-interrupted-after-active.json \
  --output-root tmp/demo/shared-tui-tracking-demo-pack/authoring/claude/claude_interrupted_after_active/capture
```

3. Read `recording/pane_snapshots.ndjson` directly and author `recording/labels.json` over the full tracked field set:
   - `diagnostics_availability`
   - `surface_accepting_input`
   - `surface_editing_input`
   - `surface_ready_posture`
   - `turn_phase`
   - `last_turn_result`
   - `last_turn_source`
   - For Claude fixtures, do not treat visibly styled startup suggestions or trust-screen selections as `surface_editing_input=yes` by default; depending on the presentation, replay may classify those spans as `unknown` or `no`, so confirm them against `recorded-validate` output before committing labels.
   - For repeated intentional-interruption fixtures, distinguish at least `active-turn-1`, `interrupted-ready-1`, `active-turn-2`, `interrupted-ready-2`, and the final post-close diagnostics-loss span so the second-turn reset and the close posture are both reviewable.
   - For the complex success-interrupt-success fixtures, also distinguish the first settled-success span, both `ready-draft` spans with `last_turn=none`, both `active-draft` spans with `surface_editing_input=yes`, and the final settled-success span.
4. Run fast replay validation without video:

```bash
bash scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate \
  --fixture-root tmp/demo/shared-tui-tracking-demo-pack/authoring/claude/claude_interrupted_after_active/capture \
  --output-root tmp/demo/shared-tui-tracking-demo-pack/authoring/claude/claude_interrupted_after_active/validation-skip-video \
  --skip-video
```

5. Fix labels or recapture until replay mismatches are zero.
6. After recording and state labeling are done, generate the MP4 visualization from the labeled pane snapshots. Unless overridden, the MP4 uses the same cadence as the underlying capture:

```bash
bash scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate \
  --fixture-root tmp/demo/shared-tui-tracking-demo-pack/authoring/claude/claude_interrupted_after_active/capture \
  --output-root tmp/demo/shared-tui-tracking-demo-pack/authoring/claude/claude_interrupted_after_active/validation
```

7. Inspect `analysis/summary_report.md`, any `issues/*.md`, and `review/review.mp4`.
8. Promote only the canonical replay artifacts into `tests/fixtures/shared_tui_tracking/recorded/<tool>/<case>/`.
9. After a promotion batch, rerun corpus validation:

```bash
bash scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate-corpus
```

### Canonical Fixture Contents

Each committed case keeps only the canonical replay-grade artifacts:

- `fixture_manifest.json`
- `runtime_observations.ndjson`
- `recording/manifest.json`
- `recording/pane_snapshots.ndjson`
- `recording/input_events.ndjson` when explicit-input authority matters
- `recording/labels.json`

Temporary authoring outputs stay under `tmp/` unless a later change decides to publish them:

- `analysis/summary_report.md`
- `analysis/groundtruth_timeline.ndjson`
- `analysis/replay_timeline.ndjson`
- `analysis/comparison.json`
- `issues/*.md`
- `review/frames/frame-*.png`
- `review/review.mp4`
