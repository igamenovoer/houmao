# Label Public TUI States

## Workflow

1. **Verify blind-label admission.** Require a stopped, digested source recording and refuse to use any tracker-generated artifact.
2. **Prepare tracker-free review material.** Use raw pane snapshots and `session.cast`, with sample IDs and elapsed time visible.
3. **Segment the source timeline into complete, non-overlapping ranges.** Mark operation boundaries, surface changes, ambiguous spans, and settle boundaries.
4. **Assign all eight public fields and evidence to every range.** Follow [../references/state-labeling.md](../references/state-labeling.md).
5. **Validate coverage and freeze the labels.** Resolve gaps, overlaps, reversed ranges, invalid values, and recording-digest mismatches before replay.
6. **Record reviewer provenance and label digest.** State uncertainty in evidence notes; never consult current detector output to settle it.

If the recording contains an unfamiliar provider surface or an interaction that the rubric does not resolve, use the native planning tool to create an explicit adjudication plan based only on raw terminal, runtime, and input evidence, then label unresolved samples as `unknown` where the public vocabulary permits it.

## Blind-Label Admission

Require all of the following:

- `capture/frozen-evidence.json` matches the current recording bytes.
- The source recorder is stopped.
- No labeler has inspected `state_observed*.ndjson`, `parser_observed*.ndjson`, replay timelines, detector traces, gateway TUI state, or comparison output for this capture.
- The label destination is new, normally `<run-root>/labels/labels.json`.

If tracker artifacts already exist, do not delete evidence to conceal the contamination. Record the attempt as non-independent and start a fresh label pass with a reviewer who has not seen the output, or classify the labels as engineering annotations rather than ground truth.

## Review Material

Play the cast for human timing context:

```bash
pixi run asciinema play "<run-root>/capture/recording/session.cast"
```

Use `pane_snapshots.ndjson` for exact sample IDs and full pane text. A blind video may be created from `render_unlabeled_review_frames()` and `encode_review_video()` in `houmao.demo.shared_tui_tracking_demo_pack.review_video`; it must contain no detector or replay fields.

## Authoring Labels

Use inclusive ranges to avoid one label per 20 Hz sample. The maintained writer is:

```bash
pixi run python -m tools.terminal_record add-label \
  --run-root "<run-root>/capture/recording" \
  --output-dir "<run-root>/labels" \
  --label-id "<stable-range-name>" \
  --scenario-id "<case-id>" \
  --sample-id "<first-source-sample>" \
  --sample-end-id "<last-source-sample>" \
  --diagnostics-availability "<value>" \
  --surface-accepting-input "<yes|no|unknown>" \
  --surface-editing-input "<yes|no|unknown>" \
  --surface-ready-posture "<yes|no|unknown>" \
  --surface-pending-input "<yes|no|unknown>" \
  --turn-phase "<ready|active|unknown>" \
  --last-turn-result "<success|interrupted|known_failure|none>" \
  --last-turn-source "<explicit_input|surface_inference|none>" \
  --evidence-note "<raw visible or runtime evidence>"
```

Every label used as ground truth must include all eight fields. `surface_pending_input` describes provider-native submitted input waiting behind an active turn, not a composer draft, Houmao prompt note, or gateway-durable request. Do not use the legacy `readiness_state` or `completion_state` fields as comparison authority.

## Readiness Adjudication

`surface_ready_posture=yes` means a prompt submitted at that sample would begin processing immediately, not merely that the editor accepts typing. Use the recorded next submission and its immediate aftermath as operational evidence:

- immediate new-turn activity supports ready
- typed text retained while the previous turn continues supports editing but not ready
- a CLI-owned queue or deferred prompt supports not ready
- an ambiguous composer with no decisive outcome supports `unknown`

Never infer ready solely from a prompt glyph, visible editor, or `surface_accepting_input=yes`.

## Completion and Freeze Gate

Expand ranges conceptually over every source sample and require complete, non-overlapping coverage. The demo validator enforces this when `recorded-validate` runs; before replay, perform the same checks without viewing replay output.

Write `<run-root>/labels/labels-manifest.json` with:

- source recording digest
- labels digest
- labeler and reviewer identifiers or roles
- labeling timestamp
- public-state schema version
- settle-seconds assumption
- independence declaration
- known ambiguities

Once frozen, do not edit labels to make a replay pass. Corrections require a new label revision with rationale and a new digest.
