## Context

The repository currently has three distinct implementations of tracked TUI semantics:

- the official live tracker in `src/houmao/server/tui/tracking.py`,
- recorder replay in `src/houmao/terminal_record/service.py` via `houmao.demo.cao_dual_shadow_watch.monitor.AgentStateTracker`, and
- the Claude explore harness replay reducer in `src/houmao/explore/claude_code_state_tracking/state_reducer.py`.

Not all of this duplication is accidental. The dual-shadow-watch demo is intended to remain an independent reference implementation that shows what correct state tracking should look like. The actual problem is that the official/runtime path does not have one owned reduction layer of its own: the server owns the official public `surface` / `turn` / `last_turn` contract, recorder replay still emits demo-era readiness/completion fields by importing the demo tracker, and the explore harness mirrors the simplified public contract in a separate reducer. The recent circular import fixed by lazy package exports showed that this is not just semantic duplication; the official/runtime layering is confused enough that generic code can end up importing demo and server runtime code transitively.

The repository already has one lower-level reusable building block in `houmao.lifecycle`: ReactiveX timing over `LifecycleObservation`, `TurnAnchor`, readiness snapshots, and anchored completion snapshots. The missing layer is the shared tracked-state core above that timing kernel and below server/demo/replay adapters.

## Goals / Non-Goals

**Goals:**

- Establish one repo-owned tracking core for parsed TUI observations and public tracked-state reduction.
- Remove the dependency from `terminal_record` into `houmao.demo.cao_dual_shadow_watch`.
- Make live server tracking, recorder replay, and the explore harness consume the same tracked-state semantics.
- Preserve the existing official server-facing `surface` / `turn` / `last_turn` behavior while moving ownership below the server adapter layer.
- Support offline replay with optional runtime diagnostics and optional recorded input authority, not just live tmux/server input.
- Preserve the dual-shadow-watch demo as an intentionally independent reference tracker rather than folding it into the official/runtime core.

**Non-Goals:**

- Replacing the content-first groundtruth classifier in the explore harness.
- Rewriting the legacy CAO dual-shadow-watch demo UI in the same change unless it must adapt to renamed replay fields.
- Preserving the old recorder replay schema as a first-class compatibility contract.
- Moving tmux discovery, process inspection, or server registration logic into the shared tracking core.

## Decisions

### Decision: Create a neutral `shared-tui-tracking-core` layer for the official/runtime path, not for the reference demo

The change will introduce a neutral package below `houmao.server`, `houmao.terminal_record`, and official/runtime replay ownership. That package will own:

- normalized tracked-state models,
- reducer state and public-state emission,
- lifecycle reduction composed from `houmao.lifecycle`,
- turn-signal interpretation needed for `surface`, `turn`, and `last_turn`, and
- optional input/runtime evidence hooks used by both live and offline adapters.

The live server tracker becomes an adapter around this core rather than the only full implementation of tracked-state semantics. The independent dual-shadow-watch demo remains a separate implementation and is not refactored to consume this core.

Rationale:

- importing `houmao.server.tui.tracking.LiveSessionTracker` directly from replay code would keep the wrong dependency direction,
- importing `houmao.demo` from generic tooling is already proven fragile, and
- the official/runtime path needs one owned semantic center even if the reference demo remains separate by design.

Alternatives considered:

- Keep the lazy `__init__` fix only.
  Rejected because it removes the import-cycle symptom but leaves duplicated semantic ownership unchanged.
- Make replay import the current server tracker directly.
  Rejected because the current tracker is still a live adapter with server/session concerns and route-model coupling.

### Decision: The shared core will consume `houmao.lifecycle`, not replace it

`houmao.lifecycle` remains the lower-level timing kernel for readiness and anchored completion streams. The new shared core will compose that kernel with:

- parsed-surface to lifecycle-observation mapping,
- turn-signal detection,
- state-signature stability handling,
- public `surface` / `turn` / `last_turn` mapping, and
- optional input/runtime evidence handling.

Rationale:

- the timing kernel already solves the hard Rx timing problem and has existing test coverage,
- the missing reuse is at the tracked-state reduction layer above it, and
- pushing public tracked-state semantics down into `houmao.lifecycle` would make that package less reusable and more server-shaped.

Alternatives considered:

- Keep separate Rx implementations in the explore harness and server.
  Rejected because that preserves semantic drift risk.
- Move all tracking logic into `houmao.lifecycle`.
  Rejected because public tracked-state semantics are higher-level than generic lifecycle timing.

### Decision: The official/runtime detector layer moves below `server` and `explore`

The shared official/runtime tracking stack will own one detector boundary for supported tools below `houmao.server` and `houmao.explore`.

For v1, that means:

- bundled official/runtime detector implementations for supported tools live with the shared core or an immediately adjacent lower package,
- live server tracking, terminal-record replay, and harness replay all consume that official/runtime detector boundary, and
- the explore harness groundtruth path may keep separate content-first detectors because it is intentionally an independent reference path.

This change does not introduce a general plugin mechanism. The immediate goal is to remove the current upward dependency from `src/houmao/server/tui/turn_signals.py` into `houmao.explore` while giving the official/runtime path one owned detector layer.

Rationale:

- the current detector bridge already violates the intended layer boundary by importing the Claude detector from `houmao.explore`,
- leaving detector ownership implicit would allow the extraction to preserve the same dependency inversion in a different package, and
- detector ownership is part of the official/runtime semantic center, not just an implementation detail.

Alternatives considered:

- Keep detector implementations in `houmao.explore` and call them from the shared core.
  Rejected because it preserves the same upward dependency under a new name.
- Generalize immediately to an adapter-supplied plugin API.
  Rejected for v1 because it adds unnecessary mechanism when the actual requirement is simply to move official/runtime detector ownership below the adapter layers.

### Decision: Extract neutral tracked-state models and adapt server route models around them

The shared core will own neutral tracked-state models for:

- diagnostics,
- foundational surface observables,
- current turn posture,
- last observed turn outcome/source,
- stability metadata, and
- any internal timing/authority snapshots needed by live and replay adapters.

`houmao.server.models` will become a thin adapter or re-export boundary for route-facing state types rather than the sole owner of these semantics.

The chosen route boundary is to keep `Houmao*` names as the explicit server-facing contract while adapting or re-exporting neutral shared-core models into that boundary. This change does not rename the route contract layer.

Rationale:

- replay and harness code should not need to import server route models to use core tracking semantics,
- the current `Houmao*` model ownership encourages non-server consumers to reach into `houmao.server`, and
- extracting neutral models is cleaner than letting every non-server consumer define mirrored dataclasses.

Alternatives considered:

- Let non-server code import `houmao.server.models` directly.
  Rejected because it keeps the layering server-centric and encourages future import tangles.
- Keep separate mirrored dataclasses in each consumer.
  Rejected because that is the current drift problem in another form.

### Decision: Move replay to the official tracked-state vocabulary and treat legacy readiness/completion as non-primary

Recorder replay will keep using `pane_snapshots.ndjson` as the machine source of truth, but `state_observed.ndjson` will move to the official tracked-state vocabulary as its primary contract. At minimum, replay rows should expose the same conceptual groups the live server owns:

- diagnostics availability and relevant degraded-state fields,
- `surface.accepting_input`,
- `surface.editing_input`,
- `surface.ready_posture`,
- `turn.phase`,
- `last_turn.result`,
- `last_turn.source`.

If legacy reducer fields such as readiness/completion remain useful during migration, they may survive only as clearly secondary debug fields rather than as the primary replay contract.

The primary operator-facing authoring surface for that replay contract remains `terminal_record add-label`. That CLI will be expanded so operators can express official tracked-state expectations for diagnostics posture, `surface`, `turn`, and `last_turn` without dropping to manual JSON editing as the main workflow.

Rationale:

- the official simplified vocabulary is already the main repo contract,
- replay validation should measure the same semantics that live tracking and dashboards consume, and
- keeping old demo-era fields primary would preserve two semantic centers.

Alternatives considered:

- Keep replay output unchanged and only swap the internal reducer.
  Rejected because labels/tests would still keep the old public contract alive.
- Remove all reducer-detail fields entirely.
  Deferred; debug-only detail may still be useful during transition, but it must stop being the primary contract.
- Treat direct JSON editing as the primary label-authoring path.
  Rejected because the repository already has a native operator-facing labeling CLI and the contract shift should evolve that workflow rather than bypass it.

### Decision: Replay adapters will model explicit-input authority when recorder artifacts support it

The shared core will accept optional explicit input events in addition to parsed observations and runtime diagnostics. That allows:

- live server input to continue producing `last_turn.source=explicit_input`,
- active-mode recorder replay to recover explicit-input authority when recorder artifacts captured it, and
- passive replay to degrade naturally to `surface_inference` or `none`.

Rationale:

- recorder active mode already captures structured input evidence in some cases,
- a shared core that only supports surface inference would throw away stronger authority when it exists, and
- the public source distinction is already part of the official contract.

Alternatives considered:

- Treat all replay as surface-only inference.
  Rejected because it unnecessarily loses authority information in active-mode recordings.

### Decision: The explore harness remains independent of `houmao-server`, but no longer independent of the shared core

The explore harness will keep its content-first groundtruth classifier outside `houmao-server`. Its replay path, however, will stop mirroring tracked-state semantics in a separate reducer and instead use a harness-owned replay adapter over the shared core directly.

That replay adapter will use the official/runtime detector layer that lives below `server` and `explore`. The only intentionally separate detector logic in the harness is the content-first groundtruth path.

Rationale:

- the harness still needs an independent groundtruth path for validation,
- but replay is no longer the system under test; the tracked-state core is the system under test,
- duplicating replay logic in the harness only recreates the same semantic drift problem.

Alternatives considered:

- Keep the current “independent replay reducer” rule literally.
  Rejected because it preserves duplication now that the repo has a reusable shared core target.

### Decision: Keep the demo tracker independent and use it as a reference implementation, not as a dependency

The dual-shadow-watch demo continues to own its own state tracker and does not get rewritten to depend on the shared official/runtime core.

The official/runtime path may still compare itself against the demo tracker in tests, fixtures, or validation workflows, but generic/runtime packages SHALL NOT import the demo tracker as their implementation dependency.

Rationale:

- the demo exists to show and validate what correct state tracking looks like,
- using it as a dependency collapses the intended independence boundary, and
- keeping it independent preserves an important cross-check against regressions in the official/runtime stack.

Alternatives considered:

- Move the demo onto the shared core.
  Rejected because it destroys the independent-reference role the demo is supposed to serve.

## Risks / Trade-offs

- [Risk] The extracted core may become too server-shaped and inherit live-only assumptions. → Mitigation: keep tmux/process probing, registration, and route shaping in caller-owned adapters; core inputs must be normalized evidence, not live infrastructure handles.
- [Risk] Replay artifact schema changes will break existing tests and labels. → Mitigation: treat the replay contract shift as an explicit breaking change, update labels/tests/docs in the same change, and keep any temporary legacy fields clearly marked as debug-only.
- [Risk] Extracting models plus reducer logic in one change is broad and can introduce semantic regressions. → Mitigation: add equivalence tests that compare live server behavior before/after extraction, plus recorder/harness replay tests that assert shared-core parity.
- [Risk] The explore harness may lose some validation value if replay and live share too much code. → Mitigation: keep groundtruth separate and use the shared core only for replay/state-reduction, not for the content-first truth path.
- [Risk] The official/runtime stack may silently diverge from the independent demo reference implementation over time. → Mitigation: add explicit parity or comparison tests/fixtures that compare representative traces without making the demo implementation a dependency of generic/runtime code.
- [Risk] Legacy demo code may still reference old readiness/completion fields. → Mitigation: scope this change to generic replay/live/harness ownership first and adapt demo surfaces only where they consume the changed replay contract.

## Migration Plan

1. Introduce the shared core package with neutral models, reducer, and detector dependencies extracted from the current server tracker.
2. Adapt the official live tracker to use the core while preserving current public route behavior and diagnostics ownership.
3. Move the official/runtime detector layer below `server` and `explore`, and update replay/live adapters to use it.
4. Adapt terminal-record replay to consume the core and change replay output plus `terminal_record add-label` to the official tracked-state vocabulary.
5. Adapt the explore harness replay path to consume the same core through a harness-owned adapter while keeping groundtruth separate.
6. Add comparison coverage that keeps the independent demo tracker useful as a reference rather than an implementation dependency.
7. Update tests, labels, and docs for the new replay contract in the same rollout.

Rollback is a normal code revert. No persistent database or wire-protocol migration is required, but replay artifact consumers in this repository must be updated atomically with the code change.

## Open Questions

- Should recorder replay keep any legacy readiness/completion fields in `state_observed.ndjson` as transitional debug fields, or should the contract cut over fully in one step?
