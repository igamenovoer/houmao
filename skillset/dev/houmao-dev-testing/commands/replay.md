# Replay TUI State Computation

## Workflow

1. **Verify replay admission.** Require frozen source evidence and complete frozen labels; record provider version, detector version selection, settle time, and input/runtime evidence availability.
2. **Replay the canonical 20 Hz source.** Keep parser and public state outputs separate from the recording authority.
3. **Derive deterministic lower and irregular cadence streams from the source.** Never rerun the live task to simulate capture delay.
4. **Replay every derived stream with tagged outputs.** Preserve `source_sample_id`, interval, sampling mode, phase offset, and seed.
5. **Audit row counts, monotonic time, source mapping, and detector metadata.** Retain failed variants as evidence.
6. **Write a replay manifest** that enumerates all variants and their output paths for `compare` and `render-video`.

If a requested delay model does not fit the built-in regular, jittered, bursty, or gapped schedules, use the native planning tool to define a deterministic schedule with a seed and source mapping, then replay it through the same current tracker interface.

## Replay Admission

Do not start replay until `labels/labels-manifest.json` declares complete independent labels for the frozen recording. This ordering prevents tracker output from influencing ground truth.

Use the recorded provider version when available so profile selection matches the live tool. An explicit detector-version override is diagnostic and must be named in the replay tag; it is not the default qualification result.

## Canonical Replay

Prefer the runtime-aware recorded validator for scenario captures. It loads source pane snapshots, input events, and `capture/runtime_observations.ndjson`, then writes the current public replay timeline without rendering video:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate \
  --fixture-root "<run-root>/capture" \
  --labels-path "<run-root>/labels/labels.json" \
  --output-root "<run-root>/replay/source" \
  --tool "<provider>" \
  --observed-version "<recorded-provider-version>" \
  --settle-seconds "<label-settle-seconds>" \
  --skip-video \
  --json
```

The principal outputs are `analysis/groundtruth_timeline.ndjson`, `analysis/replay_timeline.ndjson`, `analysis/replay_events.ndjson`, and `analysis/comparison.json` under the replay output root. Comparison is emitted as a consequence of this maintained workflow, but `compare` still owns interpretation and the aggregate verdict.

For a surface-only recording with no runtime transition under test, `tools.terminal_record analyze --output-tag source` is a valid simpler path. Record that runtime observations were omitted. Do not use that path to qualify `tui_down`, pane loss, process loss, or probe-error behavior because the command currently builds replay observations with `runtime=None`.

## Cadence Matrix

Use the source capture as the only input and create a deliberate matrix. A useful default is:

| Tag | Interval | Mode | Purpose |
| --- | ---: | --- | --- |
| `10hz-regular` | `0.1` | `regular` | Modest downsampling |
| `5hz-jittered-s17` | `0.2` | `jittered` | Ordinary capture jitter |
| `2hz-regular` | `0.5` | `regular` | Documented robustness floor |
| `2hz-bursty-s23` | `0.5` | `bursty` | Closely spaced polls followed by gaps |
| `2hz-gapped-s31` | `0.5` | `gapped` | Missed capture windows |

For each variant, derive and preserve the source mapping:

```bash
mkdir -p "<run-root>/replay/streams"

pixi run python -m tools.terminal_record derive-stream \
  --run-root "<run-root>/capture/recording" \
  --output-path "<run-root>/replay/streams/pane_snapshots_<tag>.ndjson" \
  --target-sample-interval-seconds "<interval>" \
  --sampling-mode "<regular|jittered|bursty|gapped>" \
  --phase-offset-seconds "<offset>" \
  --seed "<seed>"

```

Every derived row must retain `source_sample_id` and `source_elapsed_seconds`. Vary seeds or phase offsets explicitly; never call an unlabeled random schedule reproducible.

Replay a surface-only variant with `tools.terminal_record analyze --snapshots-path ... --output-tag <tag>`. For any case that relies on runtime posture, use a run-local adapter around these maintained APIs:

- `load_fixture_inputs()` to merge runtime observations onto source observations
- `derive_sample_schedule()` from `houmao.terminal_record.schedules` to select deterministic source samples
- `dataclasses.replace()` to assign derived sample IDs/times while retaining each selected observation's runtime evidence
- `replay_timeline()` to compute the current tracker timeline

The maintained long-horizon implementation in `src/houmao/demo/shared_tui_tracking_demo_pack/long_horizon/replay.py` demonstrates this composition. Reuse the public modules and artifact shape; do not call its attempt-state workflow for an unrelated generic run.

## Replay Manifest

Write `<run-root>/replay/replay-manifest.json` with one entry per source or derived variant:

- tag and comparison kind
- snapshots path and SHA-256
- source recording SHA-256
- interval, sampling mode, phase offset, and seed
- provider and observed version
- detector name and detector version
- settle seconds
- parser/state output paths and hashes
- sample, event, and input-event counts
- status and error

Canonical source replay uses `comparison_kind=sample_exact`. Derived variants use `comparison_kind=cadence_semantic` even when source-mapped field mismatches are also calculated for diagnostics.
