# Compare Replay with Ground Truth

## Workflow

1. **Load and verify the evidence manifest.** Require matching recording and label digests plus a replay manifest with source mapping.
2. **Run strict sample-aligned comparison for the canonical source.** Compare all eight public fields and ordered transitions.
3. **Run cadence-aware semantic comparison for each derived stream.** Measure source-mapped differences, admission safety, required transition order, terminal outcome, stuck-state behavior, and drift.
4. **Classify divergences.** Separate sustained semantic errors from boundary quantization, omitted short states, missing diagnostics, and invalid evidence.
5. **Write machine-readable and human-readable comparison artifacts.** Never rewrite labels or discard failing variants.
6. **Assign the verdict with explicit limitations.** A pass applies only to the named provider/version, recording, detector, cadence matrix, and contracts.

If the use case needs a custom semantic invariant, use the native planning tool to derive it from the stated task outcomes and downstream prompt-admission needs, add it to the comparison manifest before inspecting results, then evaluate it consistently across variants.

## Canonical Exact Comparison

For the preferred runtime-aware replay path, use the already-emitted artifacts under `<run-root>/replay/source/analysis/`:

- `groundtruth_timeline.ndjson`
- `replay_timeline.ndjson`
- `comparison.json`
- `comparison.md`

Verify that their manifests bind the expected recording, labels, provider version, and settle time. Copy or summarize the comparison into `<run-root>/comparison/source.json` and `source.md` without changing the original evidence.

For a surface-only run produced by `tools.terminal_record analyze`, the generic validator is:

```bash
pixi run python -m tools.terminal_record validate \
  --run-root "<run-root>/capture/recording" \
  --labels-path "<run-root>/labels/labels.json" \
  --state-path "<run-root>/capture/recording/state_observed_source.ndjson" \
  --parser-path "<run-root>/capture/recording/parser_observed_source.ndjson"
```

Do not use the surface-only validator for a runtime-state claim. Capture its JSON output under `<run-root>/comparison/source.json`. The hard canonical contract is:

- every selected source sample matches all eight labeled fields
- sample IDs and time order align
- public transition order matches
- no false terminal result is manufactured
- no diagnostics posture mismatch is hidden

Canonical mismatches fail the current detector for this recording unless the evidence or labels are invalid. Do not relabel from the replay output.

## Cadence-Aware Comparison

Derived streams observe a quantized subset of the source. Join each replay row to ground truth through `source_sample_id`, never through the derived `sample_id` alone.

Calculate exact source-mapped field mismatches as diagnostics, then judge the variant with semantic contracts declared before results are inspected:

- required ordered state/transition sequence
- required terminal result and forbidden terminal results
- maximum first-occurrence drift from the source replay or ground-truth boundary
- eventual return to ready after a completed or interrupted turn
- no impossible oscillation caused only by sparse capture
- no stuck `active`/false-busy state after the TUI is sustainably ready
- no false-ready state while the current turn is still processing or a submitted prompt would queue

A cadence variant may omit a short-lived label or move a boundary to the nearest observed sample and still be meaningful. It fails when it changes the interaction meaning, violates an admission invariant, invents an outcome, breaks required order, or exceeds the declared drift bound.

## Admission-Critical Metrics

Treat prompt admission errors separately from generic field mismatch counts:

- `false_ready`: replay reports `surface_ready_posture=yes` or `turn_phase=ready` where ground truth says a submitted prompt would not start immediately. This can inject a prompt into a busy CLI.
- `false_busy`: replay remains non-ready over a sustained ground-truth-ready span. This can block gateway, manager, or notification prompts.
- `ready_latency_seconds`: replay-ready boundary minus ground-truth-ready boundary.
- `busy_release_latency_seconds`: time from the last active evidence to the first trustworthy replay-ready state.
- `sustained_false_busy_seconds`: total duration of false-busy spans, with boundary-only spans reported separately.

Report false-ready as a safety failure even when brief. Define a project-specific sustained threshold for false-busy before inspecting results; use `1.0` second when no stronger use-case bound exists.

## Divergence Classes

| Class | Meaning | Verdict Treatment |
| --- | --- | --- |
| `semantic` | Replay changes state meaning, order, admission safety, or outcome | Fail |
| `boundary_quantization` | Same transition appears at the nearest available derived sample | Pass with measured drift when within bound |
| `short_state_omitted` | Sparse stream cannot observe a brief state | Pass only if the predeclared semantic contract allows omission |
| `detector_regression` | Canonical current replay differs from valid independent GT | Fail |
| `label_issue` | Raw evidence contradicts or does not support GT | Invalidate comparison; revise labels as a new version |
| `recording_issue` | Missing samples, bad source mapping, taint, or runtime gap prevents judgment | Incomplete |

## Output Contract

Write `<run-root>/comparison/<tag>.json` and `<tag>.md` for every variant. Include:

- evidence digests and replay tag
- comparison kind
- sample and mismatch counts by field
- first divergence and contiguous mismatch spans
- GT and replay transition sequences
- terminal outcome checks
- false-ready, false-busy, and latency metrics
- drift bounds and observed drift
- divergence classes
- verdict: `pass`, `fail`, or `incomplete`
- limitations and artifact paths

Write `<run-root>/comparison/summary.md` with one row per variant. Do not collapse `incomplete` into either pass or fail.
