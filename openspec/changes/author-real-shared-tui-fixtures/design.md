## Context

The shared tracked-TUI demo pack now exists and the current committed corpus proves that the replay, comparison, reporting, and review-video pipeline works end to end. The remaining gap is fixture quality: the committed cases under `tests/fixtures/shared_tui_tracking/recorded/` are still lightweight authored samples rather than recordings taken from real tmux-backed Claude Code and Codex sessions.

That means the next change is mostly an execution and content-authoring effort, not a fresh harness build. The existing demo pack already provides the relevant primitives:

- live watch to scout surfaces and prompts,
- `recorded-capture` to author replay-grade temporary runs,
- `recorded-validate` to expand labels, replay, compare, and report,
- staged-frame review video generation, and
- a committed fixture corpus layout under `tests/fixtures/shared_tui_tracking/recorded/`.

The design challenge is to make the real recording pass disciplined and repeatable so maintainers do not replace the current corpus with mislabeled or low-signal real captures.

## Goals / Non-Goals

**Goals:**
- Define a maintainer-owned workflow for collecting real Claude and Codex tmux recordings with the existing demo pack.
- Lock a first-wave case matrix with concrete prompts and expected state transitions so authoring is reproducible.
- Require a promotion gate that validates labels and replay before real authoring runs become committed fixtures.
- Clarify which artifacts remain temporary authoring evidence in `tmp/` and which artifacts are promoted into `tests/fixtures/`.

**Non-Goals:**
- Rebuilding the shared tracked-TUI demo pack or changing standalone tracker semantics.
- Automating human ground-truth classification from the reducer under test.
- Committing authoring-time `review.mp4` or temporary Markdown reports into the long-lived fixture tree by default.
- Expanding the first wave to every imaginable edge case such as approval prompts or login failures.

## Decisions

### Decision: Treat this change as a real-fixture authoring campaign on top of the existing demo pack

This change will not introduce a second capture or replay path. Maintainers will use the existing `scripts/demo/shared-tui-tracking-demo-pack/` workflow for live scouting, recorder-backed capture, replay/compare, and review-video generation.

Why this approach:
- The harness was just built for exactly this job; adding a parallel “real capture” path would split behavior at the worst possible moment.
- The remaining work is mostly fixture quality control, prompt discipline, and promotion policy.

Alternatives considered:
- Add a new authoring CLI distinct from the demo pack.
  Rejected because it would create duplicate capture semantics and increase maintenance.
- Capture directly with `tools/terminal_record` as the primary path.
  Rejected because the demo pack already adds tool launch, runtime observations, replay, reporting, and review-video generation in one workflow.

### Decision: Author all real runs under `tmp/` first and promote only cleaned artifacts into `tests/fixtures/`

Real capture runs will first be written under a temporary authoring subtree such as `tmp/demo/shared-tui-tracking-demo-pack/authoring/<tool>/<case>/<stamp>/` using `--output-root`. Only after labels are complete and validation passes will the maintainer copy the minimal canonical artifact set into `tests/fixtures/shared_tui_tracking/recorded/<tool>/<case>/`.

Why this approach:
- It keeps failed experiments, ambiguous labels, and partial reports out of the committed corpus.
- It lets maintainers iterate on prompts and labels without polluting Git history.

Alternatives considered:
- Capture directly into `tests/fixtures/shared_tui_tracking/recorded/`.
  Rejected because the committed corpus should contain only curated, promotion-grade artifacts.

### Decision: Use a fixed first-wave real capture matrix with concrete prompts and expected outcomes

The first-wave canonical matrix will be:

- Claude `explicit_success`
- Claude `interrupted_after_active`
- Claude `slash_menu_recovery`
- Claude `tui_down_after_active`
- Codex `explicit_success`
- Codex `interrupted_after_active`
- Codex `tui_down_after_active`

Recommended prompt shapes:

- `explicit_success`: `Reply with the single word READY and stop.`
- `interrupted_after_active`: `Search this repository for files related to tmux and prepare a grouped summary. Think carefully before answering.`
- `tui_down_after_active`: same long-running prompt as interruption, then kill the tmux session after active posture is visible
- `slash_menu_recovery` for Claude: type `/`, wait for overlay, then dismiss with `Escape`

Why this approach:
- The prompts are short, visibly classifiable, and already align with the current detector semantics.
- The matrix covers success, interruption, ambiguity, and diagnostics-loss without exploding the first wave.

Alternatives considered:
- Start with a broader matrix including approval prompts, login failures, or permission overlays.
  Rejected because those are lower-signal and risk stalling the initial campaign.

### Decision: Ground-truth labeling will be direct-snapshot, span-based, and field-complete

Maintainers will label state spans from `recording/pane_snapshots.ndjson` directly, using `sample_id` and `sample_end_id` to cover stable spans rather than labeling every sample independently. Labels must fully specify:

- `diagnostics_availability`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`

Runtime observations will be used to justify diagnostics degradation such as `tui_down`, but label values still come from maintainer judgment over the combined evidence.

Why this approach:
- Span-based labeling reduces clerical work while still producing deterministic expanded timelines.
- Requiring the full tracked field set prevents hidden defaults from creeping into ground truth.

Alternatives considered:
- Label only terminal states or only transition points.
  Rejected because the existing expansion step expects full coverage and humans routinely miss subtle surface-field drift when only terminal outcomes are labeled.

### Decision: After recording and state labeling, the authoring flow must generate `review.mp4` before promotion

Each temporary real capture will follow this sequence:

1. scout with live watch if needed,
2. capture in `tmp/`,
3. author labels,
4. run `recorded-validate --skip-video`,
5. fix labels or rerun capture until mismatch count is zero,
6. run full `recorded-validate` to generate the staged-frame MP4 visualization from the labeled pane snapshots,
7. inspect `summary_report.md`, any `issues/*.md`, and `review.mp4`,
8. promote the canonical artifacts into `tests/fixtures/`.

Promotion requires:
- zero replay mismatches,
- full label coverage,
- a generated Markdown summary report, and
- a generated review video for human confirmation.

Why this approach:
- It separates fast label correctness checks from slower visual confirmation.
- It treats real capture quality and label quality as release gates for the corpus.

Alternatives considered:
- Generate video only after promotion.
  Rejected because the human verification step is part of the promotion gate, not an optional afterthought.

### Decision: Commit only the canonical replay artifacts, not temporary review media

The promoted fixture tree will continue to commit:

- `fixture_manifest.json`
- `runtime_observations.ndjson`
- `recording/manifest.json`
- `recording/pane_snapshots.ndjson`
- `recording/input_events.ndjson` when present
- `recording/labels.json`

Temporary authoring outputs such as `analysis/summary_report.md`, `issues/*.md`, staged frames, and `review.mp4` remain in `tmp/` unless a later change explicitly decides to publish them.

Why this approach:
- It keeps repository size under control.
- The committed corpus remains the minimum machine-checked evidence needed for replay.

Alternatives considered:
- Commit review videos and temporary reports with every canonical fixture.
  Rejected because that increases repo weight substantially without changing replay semantics.

## Risks / Trade-offs

- [Real captures will be noisier than synthetic ones] → Mitigation: scout with live watch first and use fixed prompt shapes before committing any run.
- [Maintainers may mislabel `last_turn_source`] → Mitigation: require replay validation before video, and treat source mismatches as label bugs first.
- [Diagnostics-loss cases may preserve stale visible surface fields] → Mitigation: document that `tui_down` degrades diagnostics and phase, not automatically every surface field.
- [The first-wave matrix may still miss a tool-specific ambiguity case] → Mitigation: keep wave one focused and add second-wave cases only after the initial real corpus is stable.
- [Promotion by manual copying can drift] → Mitigation: document the exact promoted file set and require corpus-wide replay validation after each promotion batch.

## Migration Plan

1. Add the operator-facing authoring plan, matrix, and promotion rules to the repo documentation/specs.
2. Capture real authoring runs under `tmp/` for the first-wave Claude cases.
3. Label, validate, and visually review the Claude authoring runs, then promote passing artifacts into the committed corpus.
4. Repeat the same process for the Codex first-wave cases.
5. Run corpus-wide recorded validation after the promotion batch.
6. Remove or replace the lightweight authored fixtures case by case once the real replacements are committed.

Rollback is straightforward because the real-capture campaign is content-first: if a promoted fixture proves bad, restore the previous committed fixture directory and rerun corpus validation.

## Open Questions

- Whether the original lightweight authored fixtures should be preserved under a separate archived fixture subtree for detector archaeology after real replacements land.
- Whether a second-wave Codex ambiguity case is needed immediately after the first-wave promotion, or only after the real first wave proves stable.
