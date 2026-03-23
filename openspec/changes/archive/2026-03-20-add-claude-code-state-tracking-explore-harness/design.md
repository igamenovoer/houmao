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
3. record enough runtime liveness evidence to distinguish live TUI, TUI-down, and target-unavailable paths,
4. classify those snapshots into content-first groundtruth,
5. replay the same recorded sequence through an online ReactiveX tracker, and
6. compare the two timelines.

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
- Allow controlled subprocess-level network fault injection to trigger Claude error surfaces deliberately during live scenario capture.
- Cover abrupt process-death diagnostics paths such as `tui_down` and `unavailable` in addition to purely visible TUI state transitions.

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
-> runtime liveness observations
-> offline groundtruth classification
-> online-style replay tracking
-> comparison report
```

This split is deliberate.

- live capture proves the state model against a real Claude surface
- runtime liveness observations provide the non-visual evidence needed for abrupt process death and target disappearance
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

The harness will also persist lightweight runtime liveness observations, for example in `runtime_observations.ndjson`, capturing at minimum:

- tmux session existence,
- tmux pane existence,
- expected Claude child-process liveness, and
- scenario-owned kill or teardown actions when they occur

Rationale:

- The harness is intentionally outside CAO and `houmao-server`.
- `active` terminal-recorder mode is designed around managed input capture through repo-owned control-input paths; that is not the main contract being tested here.
- `passive` mode keeps artifact capture simple while `drive_events.ndjson` provides the minimal authoritative control trace the harness needs.
- pane snapshots alone are not sufficient to classify abrupt `pkill` or `segfault` paths, because the visible TUI may simply stop updating without showing a stable terminal error surface.

Alternative considered: use terminal-recorder `active` mode as the primary live capture contract. Rejected for the first pass because it would couple the harness too tightly to managed-input semantics that are not necessary for state-model validation.

### 3. The live driver will support subprocess-owned network fault injection for error discovery

The harness should not rely solely on ambient failures to discover Claude error patterns. It should support controlled fault injection against the launched Claude subprocess so failure-path scenarios can be reproduced intentionally.

The preferred first mechanism is subprocess-owned syscall fault injection, for example by launching Claude under a wrapper such as:

```text
strace -f -e inject=<network-syscall>:error=<errno>:when=<selector> claude-yunwu
```

This path is preferred for the first implementation because:

- it does not require host-level network administration,
- it works at child-process scope,
- it can target startup failures and mid-turn failures deterministically, and
- it is well suited to producing reproducible TUI-visible known-failure or degraded/unknown surfaces.

The harness may also add a second mechanism later for disrupting an already-established live socket, such as duplicating a child socket descriptor and forcing `shutdown()`, but that should remain an optional extension rather than a first-pass requirement.

Fault injection should be represented as explicit scenario-step intent in `drive_events.ndjson`, including at minimum:

- injection mode,
- target syscall or disruption method,
- expected timing window, and
- whether the scenario aims to provoke `known_failure`, `unknown`, or recovery after fault

Rationale:

- The simplified state model includes narrow `known_failure` and broader `unknown` behavior, and those paths are hard to validate if they depend on accidental live network conditions.
- Controlled subprocess-level faults make error-signal discovery practical and repeatable.

Alternative considered: depend entirely on organic login/network/runtime failures during manual runs. Rejected because it is too variable and does not support reliable scenario coverage.

### 4. Abrupt process death will be treated as a diagnostics path, not as an automatic terminal outcome

The harness must distinguish:

- supported TUI process down while tmux remains observable, and
- tmux target itself no longer observable

Those paths are primarily diagnostics outcomes, not automatic `interrupted` or `known_failure` results.

For the external harness:

- if the Claude process is killed but the tmux session and pane remain observable, the groundtruth and replay outputs should converge on the equivalent of `diagnostics.availability=tui_down`
- if the tmux target disappears entirely, the groundtruth and replay outputs should converge on the equivalent of `diagnostics.availability=unavailable`
- neither abrupt path should manufacture `last_turn.result=interrupted`
- neither abrupt path should manufacture `last_turn.result=known_failure` unless a separately recognized visible crash/failure signal has been formalized

This means the harness must include explicit scenario coverage for:

- process killed, tmux still alive
- target gone or no longer observable

Rationale:

- The simplified model reserves `known_failure` for recognized visible failure signatures rather than generic process loss.
- Abrupt process death is a high-value path because it tests the boundary between visible-TUI semantics and transport/process diagnostics.

Alternative considered: infer abrupt process death only from the final visible pane state. Rejected because it is not reliable enough to distinguish `tui_down` from `unavailable`.

### 5. Claude detection will be handled by closest-compatible detector classes, not inline script logic

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

### 6. Groundtruth will be content-first and future-aware

Groundtruth classification will operate over recorded `pane_snapshots.ndjson`, optional `drive_events.ndjson`, and runtime liveness observations.

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
For abrupt process-death paths, runtime liveness observations are additional authoritative diagnostics evidence because the pane surface alone may not express what disappeared.

Rationale:

- The classifier must be stronger than the replay tracker in order to serve as an external check.
- The current-region and recency rules are critical for Claude because stale transcript content can remain visible while a newer turn is active or completed.

Alternative considered: require manual labeling for every run. Rejected for the first pass because the user explicitly wants automatic classification by content, not a human-only labeling workflow.

### 7. Replay tracking will use ReactiveX over an observation stream, not manual timer bookkeeping

The replay tracker will consume a stream of normalized snapshot observations, detector signals, and runtime diagnostics observations. All timed behavior will be expressed with `reactivex` operators.

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

### 8. The initial scenario corpus will cover the most important public turn paths, not just the happy path

The first harness should still stay small enough to implement, but it needs broader path coverage than a pure happy-path set.

The initial scenario corpus should include at minimum:

- `simple-success`
- `interrupt-after-active`
- `slash-noise-during-active`
- `current-known-failure`
- `stale-known-failure-before-later-success`
- `ready-noise-without-submit`
- `ambiguous-surface-unknown-and-recovery`
- `settle-reset-before-success`
- `startup-network-failure-injected`
- `mid-turn-network-failure-injected`
- `process-killed-tmux-still-alive`
- `target-disappeared-unavailable`

Together these scenarios validate the most important public and near-public paths:

- `turn_ready`
- `turn_active`
- `turn_unknown`
- `turn_success`
- `turn_interrupted`
- `turn_known_failure`
- stale interruption/failure suppression
- active-turn persistence despite slash-menu churn
- ready-surface local churn not manufacturing a turn
- unknown-state recovery to a known posture
- settle-reset behavior before final success
- deterministic error-path discovery through injected startup and mid-turn failures
- diagnostics-path coverage for abrupt process death and target disappearance

Rationale:

- The highest current risk is not just success/interrupted classification; it is also false active, false failure, stale-history contamination, and missed unknown/recovery behavior.
- This set covers the most important paths in the proposed model without trying to exhaust every internal graph edge.

Alternative considered: build a broad scenario library including every internal edge and every error shape in the first pass. Rejected because it would overreach the minimal harness and delay useful feedback.

### 9. Reports will compare timelines, not just single terminal outcomes

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
- diagnostics-path mismatches such as `tui_down` versus `unavailable`
- detection lag relative to groundtruth

Rationale:

- Single terminal pass/fail is not enough to debug state-model mistakes.
- The user needs to see where replay logic diverges from the raw session.

Alternative considered: produce only a pass/fail result. Rejected because it would not be useful enough for iterative signal tuning.

### 10. Newly discovered stable signals must be formalized as state-discovery signal notes

The harness is expected to reveal Claude UI patterns that were not fully modeled at proposal time. When implementation or validation uncovers a new stable and useful signal, that signal must not remain implicit in code, comments, or one-off run logs.

Instead, the workflow should record and formalize the signal as a maintained state-discovery note, using the same style as the existing Claude signal notes already being collected for the simplified state model.

At minimum, each newly formalized signal note should capture:

- the observed tool and closest-compatible version context,
- the exact or structural visible pattern,
- current-region and recency constraints,
- what state or outcome the signal supports,
- what the signal must not be mistaken for, and
- one concrete observed example surface or artifact reference

The harness design therefore has a feedback loop:

```text
live test run
-> mismatch or new stable signal found
-> inspect raw pane sequence
-> formalize signal note
-> update detector behavior
-> replay and compare again
```

Rationale:

- Signal discovery is part of the value of this harness, not just regression checking.
- Formal signal notes prevent hard-won detection knowledge from being lost in code diffs or transient logs.

Alternative considered: let implementation code be the only place where newly discovered signals are captured. Rejected because the signal contract needs human-readable documentation and reviewable examples.

## Risks / Trade-offs

- [Live Claude behavior is externally variable] → Record the observed version, keep detectors closest-compatible, and degrade unmatched cases to `unknown`.
- [Automatic prompts may complete too quickly for useful active evidence] → Keep scenario prompts tuned to create a meaningful active window and allow control actions to trigger on observed activity rather than on blind sleep.
- [Groundtruth may still bake in detector bias] → Keep groundtruth future-aware and content-first, and preserve raw run artifacts so mismatches can be audited against pane snapshots.
- [Signal rules may drift into undocumented implementation heuristics] → Require newly discovered stable signals to be recorded as formal state-discovery notes during harness development and validation.
- [Fault-injection tooling may vary across environments] → Prefer subprocess-scoped mechanisms such as `strace --inject`, detect availability explicitly, and surface skipped injection scenarios as harness output instead of silently failing them.
- [Abrupt process death may be misread as a normal terminal result] → Persist tmux/process liveness observations and treat process-loss cases as diagnostics paths unless a separate visible crash signal has been formalized.
- [Direct live runs may fail because Claude is not logged in or startup is unhealthy] → Add explicit preflight checks and surface startup failure as harness output instead of silently proceeding.
- [Explore tooling can drift into server-coupled implementation] → Keep imports out of `houmao.server.*` and treat the recorder as a raw artifact provider only.

## Migration Plan

1. Add the explore harness scaffold under `scripts/explore/claude-code-state-tracking/`.
2. Add the tmux/terminal-recorder live capture flow, runtime liveness observation artifacts, and harness-owned drive-event logging.
3. Add subprocess-owned network fault injection support for deliberate startup and mid-turn error scenarios.
4. Add the closest-compatible Claude detector and offline groundtruth classifier over recorder artifacts plus diagnostics observations.
5. Add the ReactiveX replay tracker and comparison reporting.
6. Add the first scenario set, including process-death and target-disappearance diagnostics cases, plus a minimal operator-oriented usage path for running and inspecting one scenario.
7. Record any newly discovered stable signals from live validation as formal state-discovery notes and feed them back into detector behavior.

Rollback is simple: remove the explore harness without affecting `houmao-server`, terminal recorder contracts, or the proposed public state model.

## Open Questions

- Should selected captured runs later be promoted into checked-in replay fixtures, or should this remain a tmp-root-only workflow in the first pass?
- Should the first harness expose only per-sample comparisons, or also state-interval summaries such as active window coverage and terminal latency?
- Do we want the first live driver to support only Claude Code, or should the abstraction surface be generalized enough that Codex can be added with little reshaping?
