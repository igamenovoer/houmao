## Context

The repository already has the ingredients for standalone tracked-TUI validation, but they are split across multiple layers:

- the official standalone reducer and detector stack in `src/houmao/shared_tui_tracking/`,
- tmux-backed replay-grade capture in `src/houmao/terminal_record/`, and
- older Claude-only explore/watch tooling in `src/houmao/explore/claude_code_state_tracking/`.

What is missing is one maintained, tool-agnostic validation workflow for the standalone tracker itself. The requested workflow should be delivered as a demo-pack style surface under `scripts/demo/shared-tui-tracking-demo-pack/`, following the repository's existing `scripts/demo/*` pattern. The workflow has two distinct modes:

1. recorded validation against real tmux sessions, where the same recorded pane snapshots are inspected directly, saved as ground truth, replayed through the standalone tracker, and compared; and
2. live interactive watch, where developers attach to a Claude or Codex tmux session while a separate `rich` dashboard shows the current standalone-tracker state.

Two constraints materially shape the design:

- normal harness-driven agent launches must use the most permissive supported posture so routine capture does not stall on approval or sandbox prompts; and
- human-review video must be generated from the exact pane snapshots that feed the tracker, saved as staged frames first, and encoded to 1080p `libx264` `.mp4`.
- the demo pack should remain separate from `houmao-server` and drive the standalone tracker from direct tmux probing plus recorder/runtime evidence.

## Goals / Non-Goals

**Goals:**
- Provide a generic shared-tracker validation harness for Claude and Codex without coupling the tracker core back to server/demo code.
- Reuse `terminal_record` artifacts as the evidence boundary, with `pane_snapshots.ndjson` remaining the replay source of truth.
- Make ground truth human-owned and inspectable through structured labels over official tracked-state fields instead of relying on the reducer under test.
- Preserve enough artifacts for both automated assertions and human review, including comparison outputs, transition logs, staged frames, and final review video.
- Produce a final developer-readable Markdown report for each run together with separate Markdown issue notes inside the run output directory.
- Launch live watch sessions from `tests/fixtures/agents/` so the workflow uses the repository’s actual runtime-home and credential projection model.

**Non-Goals:**
- Changing the public tracked-state vocabulary or reducer semantics in `shared_tui_tracking`.
- Making `session.cast` the authoritative replay surface.
- Preserving operator-blocked approval surfaces in the default capture workflow; normal launch posture is intentionally permissive.
- Replacing the existing Claude-specific explore harness immediately. The new workflow may borrow from it or supersede it incrementally, but this change is about the maintained shared-tracker test path.

## Decisions

### Decision: Put the operator-facing workflow in a new demo pack under `scripts/demo/shared-tui-tracking-demo-pack/`

The operator-facing implementation will live under `scripts/demo/shared-tui-tracking-demo-pack/`, with supporting Python code in a demo-owned package if needed. The shared tracker core remains reusable application logic; the new demo pack owns fixture capture, label expansion, comparison, dashboard lifecycle, and video export.

Why this approach:
- It matches the repository's established pattern for maintained runnable workflows that keep scripts, docs, and expected artifact layouts together under `scripts/demo/`.
- It keeps `shared_tui_tracking` independent from tmux, recorder, fixture-launch, and dashboard concerns.
- It allows the new workflow to reuse or wrap older explore/watch code without forcing those patterns into the runtime core.

Alternatives considered:
- Put the operator-facing workflow under `src/houmao/explore/`.
  Rejected because the user requested a `scripts/demo/<name>` implementation surface and the repo already uses demo packs for maintained runnable workflows.
- Extend the Claude-only explore harness in place and treat it as the maintained generic path.
  Rejected because the new workflow is explicitly tool-agnostic and should not inherit a Claude-only public shape or path.

### Decision: Treat structured recorder labels as the authoritative ground-truth source

Ground truth will be authored from direct inspection of the recorded pane snapshots, then stored as structured labels in `labels.json`, using official tracked-state fields such as diagnostics posture, `surface_accepting_input`, `turn_phase`, `last_turn_result`, and `last_turn_source`.

The harness will expand those labels into a complete `groundtruth_timeline.ndjson` keyed by sample id. Replay output from the standalone tracker will then be compared against that expanded timeline.

Why this approach:
- It satisfies the requirement to read the recorded session directly and classify it before replaying through the tracker under test.
- It avoids the circular mistake of generating “ground truth” with the same reducer being validated.
- It reuses the repo-owned `terminal_record add-label` contract instead of inventing a second label format.

Alternatives considered:
- Use a second independent reducer implementation as the canonical ground-truth engine.
  Rejected because it still creates another code path that can drift and become a hidden implementation dependency.
- Store only sparse labels and compare those directly.
  Rejected because per-sample expanded timelines make automated comparison and video overlays simpler and more deterministic.

### Decision: Drive the demo pack from direct tmux probing and the standalone tracker, not from `houmao-server`

The demo pack will attach to or launch tmux sessions directly, capture pane state through recorder and tmux helpers, probe runtime liveness directly, and feed those observations into the standalone shared tracker.

The demo pack will not call `houmao-server` routes or use server-owned tracking state as an intermediate source of truth.

Why this approach:
- It keeps the demo focused on the standalone tracker itself instead of mixing in unrelated server ownership, API routes, or in-memory server state.
- It preserves a clean evidence boundary: tmux pane text plus direct runtime observations go into the tracker, and the tracker output is what the demo validates or displays.

Alternatives considered:
- Use `houmao-server` as the live state source for the dashboard or replay.
  Rejected because that would make the demo depend on the larger server subsystem and would no longer isolate the standalone tracker contract.

### Decision: Use active recorder mode for harness-driven capture runs

When the harness itself launches and drives a session, it will record through `terminal_record` active mode and deliver input through the recorder-owned attach path. That preserves authoritative managed input events for turns where explicit-input provenance matters.

Passive recorder mode remains acceptable for live watch observation or for manual developer investigation, but it is not the default for harness-authored replay fixtures.

Why this approach:
- It captures `managed_send_keys` evidence without attaching extra clients to the target session.
- It keeps explicit-input versus surface-inference validation grounded in the same recorder contract already defined in the repository.

Alternatives considered:
- Drive the target pane directly while recording passively.
  Rejected because that weakens input-authority guarantees and makes `last_turn.source=explicit_input` fixtures less trustworthy.

### Decision: Default all harness-driven launches to permissive posture

Claude launches will always include `--dangerously-skip-permissions`. Codex launches will always use a runtime-home config profile whose bootstrap yields `approval_policy = "never"` and `sandbox_mode = "danger-full-access"` in `CODEX_HOME/config.toml`.

If the harness later needs intentionally blocked-overlay fixtures, those will be authored through explicitly non-default scenarios or static fixtures, not through the normal launch posture.

Why this approach:
- It matches the clarified requirement that routine capture/watch runs must not stall on unexpected operator approval prompts.
- It aligns with the repository’s supported Codex bootstrap contract instead of depending on undocumented per-run CLI flag variants.

Alternatives considered:
- Use permissive posture only for live watch and keep recorded capture mixed.
  Rejected because the same unexpected stall risk exists during automated fixture capture.
- Pass ad hoc Codex CLI flags on every launch.
  Rejected because the repository already treats profile/bootstrap config as the supported Codex posture mechanism.

### Decision: Render review video from pane snapshots, stage 1080p frames first, then encode with `ffmpeg`

The video pipeline will render terminal-style `1920x1080` PNG frames from `pane_snapshots.ndjson`, overlay ground-truth state and visible transition markers, save the frames under the run root, and only then invoke `ffmpeg` to encode `review.mp4` with `libx264`.

Expected encode contract:
- frames are persisted before encode,
- output resolution is fixed at 1080p,
- default output frame rate is `8 fps`,
- codec is `libx264`, and
- pixel format is `yuv420p` for broad playback compatibility.

The `8 fps` default applies to review-video generation only. Recorder pane snapshots still preserve their original recorded timing, and the frame-staging step expands those recorded sample deltas onto the fixed video frame rate.

Why this approach:
- The review video stays aligned with the exact machine-readable input fed into the tracker.
- Persisted frames make visual debugging and re-encoding possible without re-running capture.
- `ffmpeg` is a stronger and more explicit encoding boundary than relying on Python video writers for the final `.mp4`.

Alternatives considered:
- Encode directly from in-memory Python frames.
  Rejected because the staged-frame requirement is explicit and staged frames are useful debugging artifacts.
- Render from `session.cast`.
  Rejected because the recorder contract defines pane snapshots, not casts, as the replay source of truth.

### Decision: Keep live watch artifact layout parallel to recorded validation and nested under the demo-pack-owned `tmp/demo/` subtree

The live watch workflow will write under a dedicated subtree such as `tmp/demo/shared-tui-tracking-demo-pack/live/<tool>/<run-id>/`. Recorded validation runs will use a sibling subtree such as `tmp/demo/shared-tui-tracking-demo-pack/recorded/<case-id>/`.

Each live run will keep:
- run-local runtime artifacts generated from fixture brains,
- recorder artifacts,
- runtime observations,
- latest state,
- state samples,
- transitions,
- final offline replay/comparison outputs when the run stops,
- one Markdown summary report, and
- zero or more issue Markdown documents under an issue-specific output subdirectory.

Why this approach:
- Developers can inspect one stable run root instead of reconstructing state from multiple unrelated directories.
- Recorded and live workflows share the same evidence model but stay operationally separate.

Alternatives considered:
- Reuse the old Claude-only `tmp/explore/claude-code-state-tracking/...` layout.
  Rejected because the new workflow is generic and should not inherit Claude-specific paths.

### Decision: Finalize each run with one summary Markdown report plus separate issue Markdown files

Every recorded-validation or live-watch run will end with a human-readable Markdown report in the run output directory. That report will summarize the run, list which checks or scenarios worked, list which did not, and point to the key raw and derived artifacts.

When the run detects one or more failures, mismatches, or other actionable issues, the workflow will also write one Markdown file per issue under a stable issue directory inside the same run root.

Why this approach:
- Developers need a compact summary artifact in addition to machine-readable NDJSON and JSON files.
- Separate issue documents make it easier to hand off individual failures without forcing developers to mine a single long report.

Alternatives considered:
- Emit only machine-readable comparison outputs.
  Rejected because that leaves too much interpretation work to developers.
- Put every issue inline in one large report.
  Rejected because per-issue Markdown files are easier to inspect, diff, and link individually.

## Risks / Trade-offs

- [Ground-truth authoring is time-consuming] → Mitigation: keep labels sparse at authoring time but require deterministic expansion and coverage validation before fixtures are accepted.
- [Live recorder active mode may still be tainted by accidental extra tmux clients] → Mitigation: preserve recorder taint metadata, fail fixture publication when authoritative capture is lost, and reserve passive mode for manual investigation only.
- [Rendered 1080p frame sets can be large] → Mitigation: scope frame retention to review runs and keep encoded video plus labels/comparison as the primary published evidence.
- [Tool-specific launch behavior may drift independently of the tracker] → Mitigation: keep permissive launch posture in recipe/config fixtures, not scattered shell strings, and add unit coverage around launch metadata.
- [Genericizing the old Claude-only watch flow may tempt partial duplication] → Mitigation: extract shared runtime/watch utilities first and keep tool-specific behavior limited to detector selection, recipe choice, and supported-process probing.
- [Server-adjacent helpers may creep back in through convenience imports] → Mitigation: keep demo-pack dependencies limited to tmux helpers, recorder lifecycle, brain-home construction, and standalone tracker APIs, and reject `houmao-server` route/state dependencies in review.
- [Report generation could drift from the underlying machine evidence] → Mitigation: generate Markdown reports directly from the persisted comparison, transition, and artifact metadata instead of from separate ad hoc logic.

## Migration Plan

1. Add the new demo pack under `scripts/demo/shared-tui-tracking-demo-pack/` together with any supporting demo-owned Python package and tests, without deleting the existing Claude-only explore harness immediately.
2. Introduce initial recorded fixtures and review-video generation for the minimum supported case set.
3. Add live watch support for Claude and Codex using fixture-backed runtime-home generation and permissive launch posture.
4. Wire automated tests to consume committed recorded fixtures only; fixture capture remains an explicit maintainer workflow.
5. After the new workflow proves stable, optionally make any older Claude-specific wrappers delegate to the shared implementation rather than maintaining two separate codepaths.

Rollback is straightforward because this change is additive: remove the new harness entrypoints and fixtures, and the existing standalone tracker plus recorder contracts remain intact.

## Open Questions

- Whether the new generic harness should fully replace the existing Claude-only explore package in a follow-up change, or coexist indefinitely as the maintained path while the older package remains historical/reference tooling.
- Whether review videos should be committed for all canonical fixtures or generated on demand from committed pane snapshots and labels to keep repository size under control.
