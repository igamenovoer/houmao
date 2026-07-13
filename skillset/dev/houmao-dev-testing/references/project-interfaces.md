# Current Houmao Testing Interfaces

## Workflow

1. **Use the scenario demo** when the task can be expressed as supported TUI actions and needs launch plus capture orchestration.
2. **Use the terminal recorder CLI** for an already-running tmux session, labels, stream derivation, current replay, and exact validation.
3. **Use the shared replay and review modules** when a generic composition needs Python-level access.
4. **Check `--help` and local source** before changing a command copied into a durable test definition.
5. **Record the exact command and version** in the run manifest.

If the maintained interfaces cannot express a required operation, use the native planning tool to build the smallest run-local adapter on the public Python functions below; do not copy service implementations into the skill.

## Supported Providers

The maintained recorder and demo support:

- `claude`
- `codex`
- `kimi`

Gemini CLI is outside this skill and must not appear in a test matrix.

## Scenario Launch and Capture

Entrypoint:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh --help
```

Relevant commands:

- `recorded-capture`: launch one real TUI, record it, and retain runtime/drive evidence
- `recorded-validate`: expand labels, replay current tracking, compare, report, and render a review video
- `recorded-sweep`: evaluate configured cadence variants against a predeclared transition contract
- `start`, `inspect`, `stop`, `cleanup`: live-watch lifecycle and recovery
- `long-horizon ...`: maintained pressure-suite workflow, not the generic default for an arbitrary task description

Scenario schema source: `src/houmao/demo/shared_tui_tracking_demo_pack/scenario.py`.

Supported actions:

- tracker-free: `wait_seconds`, `wait_for_pattern`, `send_text`, `send_key`, `interrupt_turn`, `close_tool`, `kill_supported_process`, `kill_session`
- detector-backed: `wait_for_ready`, `wait_for_active`, `wait_for_interrupted_signal`, `wait_for_interrupted_ready`

Do not use detector-backed waits in the canonical blind recording. They remain useful in engineering-only automation that is explicitly not used as independent ground truth.

The checked-in `high_rate_authoring` profile captures at 20 Hz. Explicit `--sample-interval-seconds 0.05` should still be recorded in the command and resolved config.

## Terminal Recorder

Entrypoint:

```bash
pixi run python -m tools.terminal_record --help
```

Commands:

- `start`, `status`, `stop`
- `add-label`
- `derive-stream` with `regular`, `jittered`, `bursty`, or `gapped`
- `analyze`
- `validate`

Use active mode when exact managed input events matter. Use passive mode only when observation must not claim the input path; it produces output-only capture authority.

The recorder targets an existing tmux pane and does not launch the agent. The maintained scenario demo composes launch and active recording for repeatable cases.

`tools.terminal_record analyze` currently replays pane snapshots and input events with `runtime=None`. It is appropriate for surface-only detector work. Use the recorded validator or Python replay composition when runtime observations determine `tui_down`, pane/process loss, or probe-error state.

## Python Interfaces

Replay:

- `houmao.shared_tui_tracking.reducer.replay_timeline`
- `houmao.demo.shared_tui_tracking_demo_pack.groundtruth.load_fixture_inputs`
- `houmao.demo.shared_tui_tracking_demo_pack.groundtruth.expand_labels_to_groundtruth_timeline`
- `houmao.demo.shared_tui_tracking_demo_pack.comparison.compare_timelines`

Review video:

- `houmao.demo.shared_tui_tracking_demo_pack.review_video.render_unlabeled_review_frames`
- `houmao.demo.shared_tui_tracking_demo_pack.review_video.render_review_frames`
- `houmao.demo.shared_tui_tracking_demo_pack.review_video.encode_review_video`
- `houmao.demo.shared_tui_tracking_demo_pack.review_video.build_ffmpeg_command`

The stock labeled review renderer displays terminal content plus ground truth. A detector-comparison overlay needs a generic run-local join of ground-truth and replay timelines.

## Provider Preflight

Use repository-maintained local auth bundle defaults:

- Claude: `tests/fixtures/auth-bundles/claude/kimi-coding/`
- Codex: `tests/fixtures/auth-bundles/codex/yunwu-openai/`
- Kimi: `tests/fixtures/auth-bundles/kimi/personal-a-default/` when locally provisioned

For Codex, require a reachable proxy at `127.0.0.1:7990` and set upper- and lower-case HTTP, HTTPS, and all-proxy environment variables to `http://127.0.0.1:7990` before launch. Record variable names and the URL only.

All TUI tests use unattended prompt mode. If the provider still shows an unavoidable hard-coded confirmation, capture it as an upstream exception and mark the affected automated flow incomplete unless the test specifically covers that behavior.

## Maintained Documentation

- `docs/reference/terminal-record/index.md`
- `docs/developer/terminal-record/index.md`
- `docs/reference/tui-tracking/state-model.md`
- `docs/reference/tui-tracking/replay.md`
- `scripts/demo/shared-tui-tracking-demo-pack/README.md`
- `scripts/demo/shared-tui-tracking-demo-pack/GT_STATE_COMPARISON_CONTRACT.md`
