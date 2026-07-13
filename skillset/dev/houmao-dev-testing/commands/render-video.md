# Render Review Video

## Workflow

1. **Choose the video purpose.** Select blind review, ground-truth review, or detector-comparison review and verify its required predecessor artifacts.
2. **Join frames to immutable source samples.** Use pane snapshots as the visual source and `source_sample_id` for any derived timeline.
3. **Render a lower-rate, legible frame sequence.** Default to 5 fps review playback while preserving elapsed time and source sample identity.
4. **Encode MP4 with the maintained H.264 settings.** Keep staged frames until frame and duration checks pass.
5. **Verify content and media metadata.** Check first, transition, divergence, and final frames; compare expected versus encoded frame count and duration.
6. **Persist the video manifest and digest.** State which panels are authoritative and which are computed.

If the requested composition is not supported by the maintained renderer, use the native planning tool to build a run-local adapter around the project review-video primitives, keeping sample joins and panel provenance explicit, then render and verify it.

## Video Modes

| Mode | Required Inputs | Allowed Before Label Freeze | Required Panels |
| --- | --- | --- | --- |
| `blind` | Frozen source snapshots | Yes | terminal, source sample ID, elapsed time; no tracker or GT |
| `ground-truth` | Frozen source plus frozen labels | No | terminal plus all seven GT fields and GT transition marker |
| `detector-comparison` | Frozen source, GT timeline, replay timeline, comparison | No | terminal, GT, current replay, mismatch/admission marker |

Never call a ground-truth or detector-comparison video blind.

## Maintained Ground-Truth Video Path

The recorded validator expands complete labels, replays the current tracker, writes comparison artifacts, and produces the maintained terminal-plus-GT review video:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate \
  --fixture-root "<run-root>/capture" \
  --labels-path "<run-root>/labels/labels.json" \
  --output-root "<run-root>/review/ground-truth" \
  --tool "<provider>" \
  --observed-version "<recorded-provider-version>" \
  --settle-seconds "<label-settle-seconds>" \
  --review-video-fps 5 \
  --json
```

The MP4 is `<run-root>/review/ground-truth/review/review.mp4`. The maintained renderer uses `ffmpeg`, `libx264`, `yuv420p`, CRF 18, and `+faststart`.

This video displays the terminal and ground truth. The replay and exact comparison remain authoritative in `analysis/replay_timeline.ndjson` and `analysis/comparison.json`; do not claim that the stock video overlays current detector state.

## Blind Review Path

Before tracker output exists, use `load_fixture_inputs()`, `render_unlabeled_review_frames()`, and `encode_review_video()` from:

- `houmao.demo.shared_tui_tracking_demo_pack.groundtruth`
- `houmao.demo.shared_tui_tracking_demo_pack.review_video`

Write the output under `<run-root>/labels/blind-review.mp4`. The frames must show only terminal content, source sample ID, elapsed time, and a tracker-unavailable notice.

## Detector-Comparison Path

When visual verification needs GT and current computation together, create a run-local renderer that:

1. Loads the same source snapshots used by ground truth.
2. Loads `analysis/groundtruth_timeline.ndjson` and `analysis/replay_timeline.ndjson`.
3. Joins canonical rows by `sample_id`; joins cadence variants through `source_sample_id`.
4. Renders terminal text, the seven GT fields, the seven replay fields, detector name/version, and comparison classification.
5. Highlights false-ready, sustained false-busy, semantic mismatch, and boundary-only mismatch differently.
6. Uses `encode_review_video()` or `build_ffmpeg_command()` from the maintained review-video module.

Do not import or modify a use-case-specific renderer merely because it looks similar. Keep the adapter generic to the run artifact contract.

## Verification

Run `ffprobe` on the MP4 and save JSON metadata for codec, pixel format, width, height, frame rate, frame count, and duration. Verify:

- source sample and elapsed time are visible
- the first frame, every state transition, every mismatch boundary, and the final frame have the expected labels
- no ANSI escape text corrupts the terminal panel
- frame count and duration agree with the rendered schedule within one frame
- representative extracted frames match the video mode
- SHA-256 is recorded after final encoding

Write `<run-root>/review/<mode>/video-manifest.json` with input hashes, timeline paths, renderer path/version, fps, codec, dimensions, frame count, duration, representative frame paths, output path, and output digest.
