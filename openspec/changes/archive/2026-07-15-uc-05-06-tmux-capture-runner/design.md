## Context

The goal is to collect labeled tmux recordings that cover the full prompt-queue lifecycle across Claude Code, Codex CLI, and Kimi Code. Each recording must show:

```
ready → first prompt → processing → second prompt while processing
  → pending visible → pending consumed → processing again → done → ready
```

A future detector will learn to predict, from a raw pane snapshot, whether the CLI currently accepts input (`can_accept_input`) and whether it already holds a pending message (`has_pending_message`). The recording must be tracker-blind so the labels remain independent ground truth.

The existing shared TUI tracking demo pack can launch providers and capture snapshots, but it has no lifecycle-shaped procedure for this sequence. The long-horizon harness knows how to launch unattended Claude/Codex/Kimi sessions, copy the Boltons fixture, discover the tmux pane, and clean up. This runner reuses those launch/capture/cleanup pieces and adds a small lifecycle orchestrator.

## Goals / Non-Goals

**Goals:**
- Provide a single command that captures one complete prompt-queue lifecycle for one provider.
- Produce a frozen 20 Hz recording plus a per-snapshot label template that satisfies the artifact contract in `.kimi-code/skills/houmao-dev-testing/references/artifact-contract.md`.
- Drive the lifecycle through direct tmux input so the capture works today without new `houmao-mgr` flags.
- Preserve failed or tainted attempts so they can be inspected rather than deleted.

**Non-Goals:**
- Submitting prompts through `houmao-mgr gateway prompt` or testing gateway guard behavior. Those are out of scope for this training-data change.
- Automatically generating ground-truth labels. Labeling remains a manual, tracker-blind step after the recording is frozen.
- Replaying the recording or training the detector. The runner only collects and labels raw evidence.
- Supporting any provider other than Claude Code, Codex CLI, and Kimi Code, or adding Gemini CLI.
- Modifying any source code under `src/houmao/`. This change is strictly a test-data collection harness.

## Decisions

### Reuse the long-horizon launcher for session setup

The runner imports `houmao.demo.shared_tui_tracking_demo_pack.long_horizon.orchestrator` and `projects` to copy the Boltons fixture, build the launch command, and create the tmux session.

**Rationale:** The long-horizon harness already launches all three providers unattended and records provider-version manifests. Reusing it keeps launch/capture/cleanup semantics consistent with UC-02.

**Alternative considered:** A standalone launcher. Rejected because it would duplicate provider-specific unattended logic and drift out of sync.

### Drive the lifecycle through tmux input, not gateway commands

The runner submits prompts by sending literal keystrokes to the provider tmux pane (`send_text` followed by `Enter`). The second prompt is injected while the visible surface still shows active-turn evidence.

**Rationale:** This avoids every dependency on `houmao-mgr` force flags, gateway admission logic, and provider-specific refusal behavior. The provider's native queue/retention surface is exactly what the detector needs to learn.

**Alternative considered:** Using `houmao-mgr gateway prompt --force` for the second prompt. Rejected because it is a gateway-qualification path, not a raw training-data path, and the required force semantics are not part of this change.

### Use `tools.terminal_record` active mode for the canonical recording

The runner starts `tools.terminal_record start --mode active` against the provider tmux pane at `0.05` s intervals and stops it after the final settled ready hold.

**Rationale:** Active mode captures managed input events alongside pane snapshots, which lets reviewers correlate label boundaries with exact input events.

### One lifecycle manifest per provider

Each provider has a JSON manifest that declares the exact prompts, wait patterns, hold durations, and provider-specific cues for the lifecycle. The runner executes the manifest step by step.

**Rationale:** Provider behavior differs enough (prompt glyphs, status rows, pending signatures, done cues) that a single generic manifest would be brittle. Per-provider manifests are reviewable and versioned.

### Binary per-snapshot label template

The runner emits a `labels.json` template where each source sample has two fields:

```json
{
  "can_accept_input": "yes|no|unknown",
  "has_pending_message": "yes|no|unknown",
  "evidence_note": "..."
}
```

Tristate values are allowed because some snapshots may be ambiguous during transitions.

**Rationale:** These are exactly the two detector targets. Keeping the label schema minimal reduces reviewer effort and avoids encoding the full seven-field public state, which is the tracker's job.

### Tracker-blind execution

The runner decides when to issue the next input using only fixed `wait_seconds` or `wait_for_pattern` checks against visible pane text. It must not call `wait_for_ready`, `wait_for_active`, or any detector-backed gate during canonical capture.

**Rationale:** The recording is intended to be independent ground truth. Using the detector under test as an oracle would make the recording useless for validating that detector.

### No source-code modifications

The runner lives entirely under `scripts/qualification/tui-prompt-admission/`. It imports existing public helpers from `src/houmao/` but does not edit tracker types, detector logic, the shared demo pack, or the gateway/CLI implementation.

**Rationale:** The user's directive limits this change to test-data collection. Any required tracker schema or CLI change is a separate product change.

### Failed attempts are preserved and tainted

If a step errors, the provider shows an unexpected confirmation, or a required pattern never appears, the runner stops, marks the attempt tainted, writes a `run_tainted` flag with reasons, and still stops the recorder and writes digests. Retries use a new numbered attempt directory.

**Rationale:** Partial evidence is still evidence. Discarding failed runs hides the reason a lifecycle could not complete.

### Strictly binary label targets

The label file contains exactly two fields per sample:

- `can_accept_input`: `yes` when the surface is ready for a new prompt, `no` when it is busy, `unknown` during ambiguous transitions.
- `has_pending_message`: `yes` when the provider visibly holds queued text for a later turn, `no` otherwise, `unknown` during ambiguous transitions.

The seven public tracked-state fields are intentionally omitted from this training-data label file.

**Rationale:** The detector being trained needs only these two decisions. Keeping the label schema minimal reduces noise and reviewer/auditor effort.

### Automated per-snapshot labeling with pattern heuristics

After the recording is frozen, the runner analyzes `pane_snapshots.ndjson` and assigns the binary labels using the same provider-specific regex patterns that drove the lifecycle (ready cue, active-turn cue, pending-message cue). The assignment is snapshot-by-snapshot, but the analyzer can operate on batches and use pattern matches rather than human visual inspection of every frame.

**Rationale:** The lifecycle already depends on identifiable visible signatures. Reusing those signatures for labeling is deterministic and reproducible. The resulting labels are then rendered into a review video so a human can spot-check spans, boundaries, and heuristic failures without inspecting raw `ndjson`.

**Alternative considered:** Manual blind labeling by a human reviewer. Rejected because the user wants an automated first pass with video validation for this training-data harness.

## Risks / Trade-offs

- **[Risk]** The first prompt may finish before the second prompt is injected, leaving no pending span.
  **Mitigation:** Use deliberately long prompts (e.g., "count to 100 slowly") and verify active-turn patterns before injecting the second prompt. If the first turn settles too early, mark the attempt tainted and retry.

- **[Risk]** Provider versions may show different pending-input signatures, breaking `wait_for_pattern` steps.
  **Mitigation:** Each provider manifest includes version-specific patterns. The first capture for a provider/version is treated as calibration; patterns that do not appear are recorded and the manifest is updated.

- **[Risk]** A provider may not queue the second prompt at all (it may treat it as steering or refuse it).
  **Mitigation:** Each provider manifest includes a calibration step that discovers the native behavior. If the provider does not produce a visible pending state, the run is marked `unsupported_pending_behavior` for that version.

- **[Risk]** Reusing long-horizon internals couples the runner to UC-02 layout assumptions.
  **Mitigation:** Import only launch, project-copy, and cleanup helpers; do not reuse UC-02 procedure compilation or checkpoints.

## Migration Plan

No production migration. Deployment is:
1. Add the runner package under `scripts/qualification/tui-prompt-admission/`.
2. Add per-provider lifecycle manifests under `scripts/qualification/tui-prompt-admission/lifecycles/`.
3. Add a Pixi task such as `pixi run tui-pending-state-capture`.
4. Document the run-root layout, label template, and freeze gate in the runner README.

Rollback is directory removal; no schema or persisted state is affected.

## Open Questions

- (none — the two previous questions about label scope and labeling automation have been resolved: two binary targets only, and labels are assigned by a pattern-based analyzer with video output for human audit.)
