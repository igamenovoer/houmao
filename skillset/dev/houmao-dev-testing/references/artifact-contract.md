# Houmao Development Test Artifact Contract

## Workflow

1. **Choose a fresh run root** under `tmp/houmao-dev-testing/` or a more specific user-provided `tmp/<subdir>`.
2. **Create only stage-owned directories** as their workflows begin; keep live capture output paths absent until launch tools create them.
3. **Write immutable input digests** at capture and label boundaries.
4. **Append replay, comparison, review, and report artifacts** without changing frozen source evidence.
5. **Preserve failed attempts and record cleanup separately.**

If an existing harness imposes a nested layout, use the native planning tool to map its paths into the logical sections below without copying or renaming authoritative files after they have been hashed.

## Logical Layout

```text
tmp/houmao-dev-testing/<run-id>/
├── definitions/
│   ├── task.md
│   └── scenario.json
├── capture/
│   ├── fixture_manifest.json
│   ├── capture_manifest.json
│   ├── drive_events.ndjson
│   ├── runtime_observations.ndjson
│   ├── frozen-evidence.json
│   └── recording/
│       ├── manifest.json
│       ├── session.cast
│       ├── pane_snapshots.ndjson
│       └── input_events.ndjson
├── labels/
│   ├── blind-review.mp4
│   ├── labels.json
│   └── labels-manifest.json
├── replay/
│   ├── streams/
│   └── replay-manifest.json
├── comparison/
│   ├── source.json
│   ├── source.md
│   ├── <variant>.json
│   ├── <variant>.md
│   └── summary.md
├── review/
│   ├── ground-truth/
│   └── detector-comparison/
└── report.md
```

`scenario.json` is optional for manually driven tests. The capture demo owns several files under `capture/`; do not duplicate them elsewhere just to make the tree exact.

## Authority

| Artifact | Authority |
| --- | --- |
| `pane_snapshots.ndjson` | Machine replay source of truth |
| `input_events.ndjson` | Input timing/source evidence when capture level permits |
| `runtime_observations.ndjson` | Tmux, pane, and supported-process liveness evidence |
| `session.cast` | Human visual review only |
| `labels.json` | Independent public-state ground truth after freeze |
| `state_observed*.ndjson` or replay timeline | Current implementation output, never ground truth |
| comparison JSON/Markdown | Derived verdict scoped to named inputs and contract |
| MP4 and extracted frames | Review aid; timelines and manifests remain machine authority |

## Immutability Gates

`capture/frozen-evidence.json` binds the task/scenario, recorder manifest, source snapshots, input events, runtime observations, and operation log. `labels/labels-manifest.json` binds that recording digest to the complete label digest.

After each gate:

- do not edit the bound files in place
- create a new revision or attempt for corrections
- record SHA-256, byte size, row count, and generation timestamp
- record missing optional files as absent rather than using an empty placeholder

## Attempt Policy

Live retries use `<run-id>-attempt-001`, `<run-id>-attempt-002`, or a harness-owned equivalent. Preserve partial source files, controller logs, taints, and errors. Replay, comparison, or encoding retries may reuse an unchanged frozen source; name their outputs by variant or renderer revision.

## Sensitive Material and Cleanup

Temporary provider homes and copied credentials are not test evidence. Keep them outside durable report bundles when the harness permits it, remove them after capture, and record cleanup status without recording values. Preserve manifests, recordings, labels, timelines, comparisons, and videos.
