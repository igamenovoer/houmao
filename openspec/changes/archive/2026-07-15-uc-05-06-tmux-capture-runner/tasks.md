## 1. Scaffold the runner package

- [x] 1.1 Create `scripts/qualification/tui-prompt-admission/tui_pending_state_capture/` package directory with `__init__.py`, `models.py`, `runner.py`, `lifecycle.py`, `pattern_poller.py`, `labels.py`, `freeze.py`, and `video.py`.
- [x] 1.2 Add dataclasses for `LifecycleManifest`, `LifecycleStep`, `StepKind`, `SendTextStep`, `SendKeyStep`, `WaitSecondsStep`, `WaitForPatternStep`, `WaitForPatternAbsentStep`, `LabelRow`, and `FrozenEvidence`.
- [x] 1.3 Add JSON schema validation for lifecycle manifests so unknown step kinds fail fast.

## 2. Reuse long-horizon launch and capture

- [x] 2.1 Import the long-horizon project-copy helper to create a fresh Boltons checkout under the run root.
- [x] 2.2 Import the long-horizon helpers to launch an unattended provider tmux session and discover the pane/session IDs.
- [x] 2.3 Start `tools.terminal_record` active-mode recording at `0.05` s before the first lifecycle input.
- [x] 2.4 Stop the recorder after the final settled ready hold, ensuring `manifest.json` has `stopped_at_utc` and `stop_reason`.

## 3. Implement tracker-blind lifecycle execution

- [x] 3.1 Implement `wait_seconds` that sleeps for the configured duration.
- [x] 3.2 Implement `wait_for_pattern` that polls the latest pane snapshot text for a regex and times out cleanly.
- [x] 3.3 Implement `send_text` that injects literal text into the tmux pane and records it as a managed input event.
- [x] 3.4 Implement `send_key` for control keys such as `Enter`, `Ctrl+C`, and `Escape`.
- [x] 3.5 Ensure none of the step handlers call detector-backed gates such as `wait_for_ready` or `wait_for_active`.

## 4. Implement the prompt-queue lifecycle

- [x] 4.1 Define lifecycle steps: wait for ready, send first prompt, wait for active, send second prompt, wait for pending signature, wait for pending signature to disappear, wait for processing to finish, wait for ready.
- [x] 4.2 Use provider-specific `wait_for_pattern` targets for active-turn, pending-message, and done cues.
- [x] 4.3 Record the elapsed times of key transitions (active onset, pending onset, pending offset, done, ready return).
- [x] 4.4 Mark the attempt tainted if the lifecycle cannot be completed and preserve partial evidence.

## 5. Implement freeze gate and taint handling

- [x] 5.1 Compute SHA-256 digests for `manifest.json`, `pane_snapshots.ndjson`, `input_events.ndjson`, `session.cast`, the lifecycle manifest, and the label template.
- [x] 5.2 Write `capture/frozen-evidence.json` with digests, byte sizes, row counts, and generation timestamp.
- [x] 5.3 On any step failure, unallowlisted confirmation, or pattern timeout, record `run_tainted` reasons, still run the freeze gate, and exit non-zero.
- [x] 5.4 Number retry attempts as `<run-id>-attempt-001`, preserving earlier complete or partial recordings.

## 6. Implement automated binary labeling

- [x] 6.1 Build a snapshot analyzer that reads `capture/recording/pane_snapshots.ndjson` and applies provider-specific ready/active/pending regex patterns to each sample.
- [x] 6.2 Emit `labels/labels.json` with exactly `can_accept_input`, `has_pending_message`, and `evidence_note` per sample; default to `unknown` when cues conflict or are absent.
- [x] 6.3 Record pattern-match evidence in `evidence_note` so human auditors can verify ambiguous frames.
- [x] 6.4 Produce a label summary (counts per class and first/last sample ids for each span) in `labels/labels-summary.json`.

## 7. Render labeled review video

- [x] 7.1 Render each snapshot as a frame with the terminal content on the left and an info panel showing sample id, elapsed time, `can_accept_input`, `has_pending_message`, and the evidence note.
- [x] 7.2 Encode frames into `review/labels.mp4` at 20 Hz using `ffmpeg`, `libx264`, `yuv420p`.
- [x] 7.3 Include the rendered video path and hash in `capture/frozen-evidence.json`.

## 8. Add per-provider lifecycle manifests

- [x] 8.1 Create `scripts/qualification/tui-prompt-admission/lifecycles/claude.json` with ready/active/pending patterns and long-running prompts.
- [x] 8.2 Create `lifecycles/codex.json` with Codex-specific pending signatures such as `Messages to be submitted after next tool call`.
- [x] 8.3 Create `lifecycles/kimi.json` with Kimi-specific composer/queued chip patterns.
- [x] 8.4 Document how to calibrate patterns for a new provider version.

## 9. Add CLI entrypoint and Pixi task

- [x] 9.1 Create `scripts/qualification/tui-prompt-admission/tui_pending_state_capture_runner.py` CLI that accepts `--provider`, `--run-root`, `--attempt`, `--skip-video`, `--list-lifecycles`, `--lifecycle`, and `--dry-run`.
- [x] 9.2 Add a `pixi run tui-pending-state-capture` task to `pyproject.toml`.
- [x] 9.3 Add a dry-run mode that prints the resolved lifecycle steps without launching a provider.

## 10. Scope guard and tests

- [x] 10.1 Verify that no new or modified files appear under `src/houmao/` as part of this change.
- [x] 10.2 Add unit tests for lifecycle manifest parsing and label-template serialization.
- [x] 10.3 Add unit tests for the snapshot analyzer and freeze-gate digest format.
- [x] 10.4 Add a smoke test that runs the lifecycle engine against a fake poller and the real Codex manifest.

## 11. Documentation and calibration

- [x] 11.1 Write a README explaining the lifecycle, run-root layout, automated labeling, review video, and freeze gate.
- [x] 11.2 Run one manual capture per provider to confirm the lifecycle reaches a visible pending state and the analyzer labels it correctly.
  - Scope-closed by maintainer direction on 2026-07-15; no additional manual capture is required.
- [x] 11.3 Record the exact provider versions and pending signatures observed during calibration in `lifecycles/<provider>-calibration.md`.
  - Scope-closed by maintainer direction on 2026-07-15; no additional calibration document is required.
