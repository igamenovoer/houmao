## Context

The proposed simplified `houmao-server` state model needs independent verification outside of the server implementation. The repository already has the right raw ingredients:

- tmux-backed live sessions
- the `claude-yunwu` wrapper as a practical Claude Code launch path
- terminal-recorder artifacts rooted in `pane_snapshots.ndjson`
- libtmux-based driving precedents
- an explicit OpenSpec state model for foundational observables, turn state, and closest-compatible versioned signal detectors

What is missing is a minimal external harness that can:

1. launch and drive Claude Code in tmux,
2. record raw pane snapshots,
3. classify those snapshots into content-first groundtruth,
4. replay the same recorded sequence through an online ReactiveX tracker, and
5. compare the two timelines.

This harness must not depend on `houmao-server` tracker code, because the point is to validate the model and the signal rules independently of the current server implementation.

## Goals / Non-Goals

**Goals:**

- Add an explore-only harness under `scripts/explore/claude-code-state-tracking/`.
- Launch `claude-yunwu` in tmux and drive repeatable scenario turns automatically.
- Record raw pane snapshots through the existing terminal recorder.
- Derive groundtruth from raw recorded content, including ANSI-aware and recency-aware Claude signal detection.
- Replay the same recorded sequence through an independent ReactiveX tracker that follows the proposed simplified state model.
- Produce a comparison report that shows where replay tracking agrees or disagrees with groundtruth.
- Keep the detector layer modular and closest-compatible by version rather than exact-version locked.

**Non-Goals:**

- Replacing or patching `houmao-server` tracking in this change.
- Turning the explore harness into a production server dependency.
- Creating a generic all-tools tracker in the first pass.
- Requiring CI-stable live Claude runs for every future repository test path.
- Solving every known-failure pattern in the initial scenario set.

## Decisions

### 1. The harness will be split into live capture, offline groundtruth, replay tracking, and comparison

The harness will have four explicit stages:

```text
live tmux session
-> recorder capture
-> offline groundtruth classification
-> online-style replay tracking
-> comparison report
```

This split is deliberate.

- live capture proves the state model against a real Claude surface
- offline groundtruth is allowed to use future context and settle lookahead
- replay tracking is restricted to past/current observations plus ReactiveX timing
- comparison highlights where online tracking fails against a stronger offline interpretation

Rationale:

- If groundtruth and replay use the same online reducer, the test becomes circular.
- Future-aware offline classification is the right place to decide success-settle boundaries and stale-history suppression.

Alternative considered: run only a replay tracker over the captured session and treat its output as truth. Rejected because it would not validate the tracker independently.

### 2. The live capture path will use the existing terminal recorder in `passive` mode plus harness-owned drive-event logging

The harness will reuse `tools/terminal_record` for raw pane capture, but its default live recording mode will be `passive`.

The harness itself will persist its own `drive_events.ndjson` recording:

- prompts sent
- control input such as `C-c`
- optional noise injections such as `/`
- timestamps and scenario-step identity

Rationale:

- The harness is intentionally outside CAO and `houmao-server`.
- `active` terminal-recorder mode is designed around managed input capture through repo-owned control-input paths; that is not the main contract being tested here.
- `passive` mode keeps artifact capture simple while `drive_events.ndjson` provides the minimal authoritative control trace the harness needs.

Alternative considered: use terminal-recorder `active` mode as the primary live capture contract. Rejected for the first pass because it would couple the harness too tightly to managed-input semantics that are not necessary for state-model validation.

### 3. Claude detection will be handled by closest-compatible detector classes, not inline script logic

The explore harness will mirror the proposed state-model architecture by introducing detector classes:

```text
BaseSignalDetector
├── ClaudeCodeSignalDetectorV2_1_X
└── FallbackSignalDetector
```

The selector will choose the closest compatible detector for the observed Claude version rather than requiring an exact version match.

The detector layer owns:

- current-region extraction from raw pane content
- stale-history suppression
- ANSI-aware error detection
- active-turn evidence detection
- interruption detection
- success-candidate detection

The detector layer does not own timed state transitions. Timed behavior remains in the replay tracker.

Rationale:

- Claude UI patterns are version-sensitive.
- Closest-compatible detector selection is already part of the proposed state-model direction.
- Keeping the detector modular lets the harness evolve as Claude UI changes without entangling the replay reducer.

Alternative considered: write one ad hoc Claude-specific parser directly inside the replay script. Rejected because it would be hard to swap, hard to test, and inconsistent with the proposed design.

### 4. Groundtruth will be content-first and future-aware

Groundtruth classification will operate over recorded `pane_snapshots.ndjson` and optional `drive_events.ndjson`.

Groundtruth may use future context for:

- stable success detection after a settle window
- stale interruption suppression
- stale known-failure suppression
- deciding whether a slash-menu overlay was noise inside a still-active turn

Groundtruth will not use:

- `houmao-server` tracker code
- `terminal_record analyze` state output as the source of truth
- blind substring matching over full scrollback

The raw pane sequence remains authoritative. ANSI-bearing raw text is part of the evidence surface.

Rationale:

- The classifier must be stronger than the replay tracker in order to serve as an external check.
- The current-region and recency rules are critical for Claude because stale transcript content can remain visible while a newer turn is active or completed.

Alternative considered: require manual labeling for every run. Rejected for the first pass because the user explicitly wants automatic classification by content, not a human-only labeling workflow.

### 5. Replay tracking will use ReactiveX over an observation stream, not manual timer bookkeeping

The replay tracker will consume a stream of normalized snapshot observations and detector signals. All timed behavior will be expressed with `reactivex` operators.

That includes at minimum:

- success settle timing
- unknown/degraded timing
- reset when later observations invalidate a pending success
- deterministic replay under a scheduler

The replay path will support both:

- recorded replay from `pane_snapshots.ndjson`
- optional live polling reuse of the same reducer

Rationale:

- The state-model change already requires ReactiveX-timed behavior.
- Using Rx here keeps the explore harness aligned with the model it is intended to validate.
- It also makes replay timing testable without real sleeps.

Alternative considered: write an imperative replay loop with mutable timestamps because it is simpler. Rejected because it would validate the wrong timing model.

### 6. The first scenario corpus will stay small and target the most valuable state boundaries

The initial harness will support a small scenario library, for example:

- `simple-success`
- `interrupt-after-active`
- `slash-noise-during-active`

These scenarios are enough to validate:

- `turn_ready`
- `turn_active`
- `turn_interrupted`
- `turn_success`
- stale-history suppression
- active-turn persistence despite slash-menu churn

Known-failure automation may be added later, but it should not block the minimal harness.

Rationale:

- The highest current risk is incorrect active/interrupted/success classification and stale-history handling.
- A narrow first corpus keeps the explore tool useful without over-designing it.

Alternative considered: build a broad scenario library including every error shape in the first pass. Rejected because failure surfaces are less stable and would slow down the minimal harness.

### 7. Reports will compare timelines, not just single terminal outcomes

The harness output should include:

- `groundtruth_timeline.ndjson`
- `replay_timeline.ndjson`
- `comparison.json`
- `comparison.md`

Comparison should highlight:

- transition order mismatches
- first divergence sample/time
- false positive terminal outcomes
- missed active intervals
- detection lag relative to groundtruth

Rationale:

- Single terminal pass/fail is not enough to debug state-model mistakes.
- The user needs to see where replay logic diverges from the raw session.

Alternative considered: produce only a pass/fail result. Rejected because it would not be useful enough for iterative signal tuning.

## Risks / Trade-offs

- [Live Claude behavior is externally variable] → Record the observed version, keep detectors closest-compatible, and degrade unmatched cases to `unknown`.
- [Automatic prompts may complete too quickly for useful active evidence] → Keep scenario prompts tuned to create a meaningful active window and allow control actions to trigger on observed activity rather than on blind sleep.
- [Groundtruth may still bake in detector bias] → Keep groundtruth future-aware and content-first, and preserve raw run artifacts so mismatches can be audited against pane snapshots.
- [Direct live runs may fail because Claude is not logged in or startup is unhealthy] → Add explicit preflight checks and surface startup failure as harness output instead of silently proceeding.
- [Explore tooling can drift into server-coupled implementation] → Keep imports out of `houmao.server.*` and treat the recorder as a raw artifact provider only.

## Migration Plan

1. Add the explore harness scaffold under `scripts/explore/claude-code-state-tracking/`.
2. Add the tmux/terminal-recorder live capture flow and harness-owned drive-event logging.
3. Add the closest-compatible Claude detector and offline groundtruth classifier over recorder artifacts.
4. Add the ReactiveX replay tracker and comparison reporting.
5. Add the first scenario set and a minimal operator-oriented usage path for running and inspecting one scenario.

Rollback is simple: remove the explore harness without affecting `houmao-server`, terminal recorder contracts, or the proposed public state model.

## Open Questions

- Should selected captured runs later be promoted into checked-in replay fixtures, or should this remain a tmp-root-only workflow in the first pass?
- Should the first harness expose only per-sample comparisons, or also state-interval summaries such as active window coverage and terminal latency?
- Do we want the first live driver to support only Claude Code, or should the abstraction surface be generalized enough that Codex can be added with little reshaping?
