# TUI Pending-State Capture Runner

This harness produces labeled tmux recordings of Claude Code, Codex CLI, and Kimi Code that cover the prompt-queue lifecycle used to train the pending-message detector.

Each run captures a prompt-queue lifecycle such as:

```text
ready → first prompt → processing → follow-up prompt while processing
  → pending visible → (additional follow-ups for count-targeted manifests)
  → pending consumed → processing again → done → ready
```

The output is a frozen 20 Hz recording plus per-snapshot labels (`can_accept_input`, `has_pending_message`, and `pending_count`) and a review video for human audit.

## Usage

List available lifecycle manifests:

```bash
pixi run tui-pending-state-capture --list-lifecycles
```

Dry-run a lifecycle to inspect resolved steps:

```bash
pixi run tui-pending-state-capture \
  --provider codex \
  --run-root tmp/houmao-dev-testing/20260714-codex-pending \
  --dry-run
```

Capture one attempt with the default single-pending manifest:

```bash
pixi run tui-pending-state-capture \
  --provider codex \
  --run-root tmp/houmao-dev-testing/20260714-codex-pending
```

Use a count-targeted manifest to exercise 1, 2, or 3 coexisting pending prompts:

```bash
pixi run tui-pending-state-capture \
  --provider codex \
  --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/codex-3-pending-long.json \
  --run-root tmp/houmao-dev-testing/20260714-codex-3-pending-long
```

The `3-pending-long` manifest includes a ~500-character canary prompt so the review video shows how a long queued message is rendered.

Skip the review video for faster iteration:

```bash
pixi run tui-pending-state-capture \
  --provider codex \
  --run-root tmp/houmao-dev-testing/20260714-codex-pending \
  --skip-video
```

## Run-root layout

For each attempt the runner creates:

```text
tmp/houmao-dev-testing/<run-id>/
  <provider>-attempt-001/
    capture/
      recording/           # terminal-record artifacts
        manifest.json
        pane_snapshots.ndjson
        input_events.ndjson
        session.cast
      lifecycle-manifest.json
      frozen-evidence.json
      run-summary.json
    labels/
      labels.json          # binary per-snapshot labels
      labels-summary.json  # span counts and first/last sample ids
    review/
      labels.mp4           # labeled review video (unless --skip-video)
```

## Lifecycle manifests

Per-provider manifests live in `scripts/qualification/tui-prompt-admission/lifecycles/`. Each manifest declares regex patterns for `ready`, `active`, and `pending` surfaces and the ordered lifecycle steps.

Supported step kinds:

- `wait_seconds`
- `wait_for_pattern`
- `wait_for_pattern_absent`
- `send_text`
- `send_key`

Prompt text can use `{{name}}` placeholders that are resolved from the manifest's `prompts` map.

## Automated labeling

After the recorder stops, `labels.py` analyzes every snapshot with the same lifecycle patterns. A snapshot is labeled:

- `can_accept_input=yes`, `has_pending_message=no`, `pending_count=0` when only the ready pattern matches.
- `can_accept_input=no`, `has_pending_message=no`, `pending_count=0` when the active pattern matches but pending does not.
- `can_accept_input=no`, `has_pending_message=yes`, `pending_count=N` when the pending pattern matches and the manifest's `pending_count_patterns` can estimate the queue depth.
- `unknown` when cues conflict or are absent.

`pending_count` is one of `0`, `1`, `2`, `3`, or `"unknown"`. It is estimated from visible queued-message markers (for example, Codex's `↳` bullets) or from a regex group. Counts above three are capped at `"unknown"` because the detector only needs to distinguish up to three coexisting pending prompts.

The `evidence_note` field records which patterns matched so a human auditor can verify ambiguous frames in `review/labels.mp4`.

## Calibration

Provider versions and pending signatures change. The initial manifests contain placeholder or best-effort patterns. To calibrate:

1. List available manifests and pick a count target (`1-pending`, `2-pending`, or `3-pending-long`).
2. Run one capture per provider.
3. Inspect `capture/frozen-evidence.json` for the observed `calibrated_version` and `observed_pending_count`.
4. Open `review/labels.mp4` and locate the pending span.
5. Copy the exact pending signature into the provider manifest's `pending.regex`.
6. Tune `pending_count_patterns` to match the provider's queued-message bullets or inline count text.
7. Update `calibrated_version` to the observed provider version.
8. Re-run and confirm the pending span is labeled correctly.

If the provider caps its pending queue below the target count, the run is marked tainted with `pending_count_capped_at_N_target_M` and still freezes the evidence so the cap is recorded.

Record calibration notes in `lifecycles/<provider>-calibration.md`.

## Tracker-blind guarantee

The runner drives the lifecycle using only fixed waits and direct visible-pattern polls. It never calls `wait_for_ready`, `wait_for_active`, or any detector-backed gate during canonical capture, so the recording remains independent ground truth.

## Scope

This harness is test-data collection only. It does not modify `src/houmao/` and does not train or validate the detector.
