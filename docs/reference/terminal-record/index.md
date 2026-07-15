# Terminal Recorder

The terminal recorder captures an already-running tmux-backed agent session for later parser and lifecycle testing. The maintained developer wrapper lives under `tools/terminal_record` and delegates to `houmao.terminal_record`.

For maintainer-oriented design notes and change guidance, see the [Terminal Recorder Developer Guide](../../developer/terminal-record/index.md).

Use the repo-managed Python environment when invoking it:

```bash
pixi run python -m tools.terminal_record start --mode active --target-session HOUMAO-gpu --tool codex
```

Recorder analysis accepts `--observed-version <version>` so replay selects the same bounded detector profile as the live session. Omitting it selects the conservative fallback profile.

Use a high-rate source capture for canonical labeling, then derive deterministic lower-cadence streams without losing source traceability:

```bash
pixi run python -m houmao.terminal_record derive-stream \
  --run-root <recording> \
  --target-sample-interval-seconds 0.5 \
  --sampling-mode jitter \
  --seed 17 \
  --output-path <recording>/pane_snapshots_2hz-jitter.ndjson
```

`--sampling-mode` supports canonical `regular`, `jitter`, `drop`, and `burst` schedules. The older internal spellings `jittered`, `gapped`, and `bursty` remain accepted for existing replay plans. Every derived row records `source_sample_id` and `source_elapsed_seconds`. Qualification derives 10 Hz, 5 Hz, and 2 Hz fixed streams plus seeded irregular variants from the frozen 20 Hz source without modifying that source. Validation maps each retained row back to its audited source label, reports labels skipped because no sample was retained, compresses mismatches into contiguous ranges, and reports pending-input transition drift against the retained cadence.

## Modes

`active`

- creates a recorder-owned tmux attach path
- records `asciinema` input frames with `--capture-input`
- publishes recorder state back into the target tmux session so repo-managed `send-keys` calls can append structured managed-input events
- starts with `input_capture_level=authoritative_managed`
- degrades to `managed_only` if the run becomes tainted, for example when extra tmux clients attach to the target session

`passive`

- observes a live tmux session without becoming the required input path
- records the visual session and pane snapshots only
- marks the run as `input_capture_level=output_only`

## Commands

Start an active run against a single-pane session:

```bash
pixi run python -m tools.terminal_record start --mode active --target-session HOUMAO-gpu --tool codex
```

Start a passive run against a specific pane:

```bash
pixi run python -m tools.terminal_record start --mode passive --target-session HOUMAO-gpu --target-pane %1 --tool codex
```

Kimi Code signal-corpus captures use the same recorder with `--tool kimi`, a repo-local run root, and a high-rate sampling interval:

```bash
pixi run python -m tools.terminal_record start \
  --mode passive \
  --target-session HMKIMI-dev-001 \
  --tool kimi \
  --run-root tmp/kimi-tui-tracking/dev-001 \
  --sample-interval-seconds 0.1 \
  --duration-seconds 30
```

Inspect a run:

```bash
pixi run python -m tools.terminal_record status --run-root tmp/terminal_record/20260319-120000-HOUMAO-gpu
```

Stop a run:

```bash
pixi run python -m tools.terminal_record stop --run-root tmp/terminal_record/20260319-120000-HOUMAO-gpu
```

Analyze recorded pane snapshots:

```bash
pixi run python -m tools.terminal_record analyze --run-root tmp/terminal_record/20260319-120000-HOUMAO-gpu
```

Derive a low-rate stream from a high-rate capture:

```bash
pixi run python -m tools.terminal_record derive-stream --run-root tmp/kimi-tui-tracking/dev-001
```

Analyze the derived stream and keep its observed outputs beside the source stream:

```bash
pixi run python -m tools.terminal_record analyze \
  --run-root tmp/kimi-tui-tracking/dev-001 \
  --tool kimi \
  --snapshots-path tmp/kimi-tui-tracking/dev-001/pane_snapshots_2fps.ndjson \
  --output-tag 2fps
```

Persist a label for a recorded checkpoint:

```bash
pixi run python -m tools.terminal_record add-label \
  --run-root tmp/terminal_record/20260319-120000-HOUMAO-gpu \
  --label-id trust-prompt-blocked \
  --scenario-id trust-prompt-recovery \
  --sample-id s000021 \
  --diagnostics-availability available \
  --surface-pending-input unknown \
  --turn-phase unknown \
  --last-turn-source none \
  --evidence-note "bounded approval panel with numbered choices"
```

Validate observations against labels:

```bash
pixi run python -m tools.terminal_record validate --run-root tmp/kimi-tui-tracking/dev-001

pixi run python -m tools.terminal_record validate \
  --run-root tmp/kimi-tui-tracking/dev-001 \
  --state-path tmp/kimi-tui-tracking/dev-001/state_observed_2fps.ndjson \
  --parser-path tmp/kimi-tui-tracking/dev-001/parser_observed_2fps.ndjson
```

## Artifact Contract

Each run writes one recorder-owned root under `tmp/terminal_record/<run-id>/` unless `--run-root` overrides it.

Important artifacts:

- `manifest.json`: recorder mode, tmux target, capture authority, taint metadata, attach command, and timing metadata
- `live_state.json`: long-running controller status used by `status` and `stop`
- `session.cast`: operator-facing `asciinema` cast produced via the repo-owned `pixi run asciinema` task backed by `extern/orphan/bin/asciinema-x86_64-unknown-linux-gnu`
- `pane_snapshots.ndjson`: exact tmux pane samples captured with `tmux capture-pane`; this is the authoritative replay surface, and each `output_text` entry can feed the standalone shared TUI tracker directly
- `pane_snapshots_2fps.ndjson`: optional derived stream produced from `pane_snapshots.ndjson`; each derived row records the selected source sample in `source_sample_id`
- `input_events.ndjson`: normalized input events when the selected mode provides managed input capture
- `parser_observed.ndjson`: parser-facing observations generated by `analyze`
- `state_observed.ndjson`: official tracked-state observations generated by `analyze`, including diagnostics posture, independent accepting/editing/ready/pending surface fields, `turn`, and `last_turn`, with any retained readiness/completion fields treated as debug-only
- `labels.json`: structured operator labels for recorded samples or sample ranges; every label requires `surface_pending_input=yes|no|unknown`

The recorder keeps `session.cast` for human review, but automated replay and testing should consume `pane_snapshots.ndjson`.

## Managed `send-keys` Integration

The existing `send-keys` path remains the runtime delivery mechanism for mixed tmux control input. When an `active` recorder is live for the same tmux-backed session, the backend's `send_input_ex()` method appends a structured `managed_send_keys` event to `input_events.ndjson` after successful tmux delivery.

This integration is additive. Recorder logging failures do not block the underlying control-input delivery.
