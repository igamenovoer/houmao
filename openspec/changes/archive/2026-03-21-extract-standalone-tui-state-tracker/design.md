## Context

The current tracked-TUI implementation is split across three different shapes:

- a shared reducer in `src/houmao/shared_tui_tracking/` that is mostly replay-oriented and expects timestamped observations,
- server-owned live tracking in `src/houmao/server/tui/tracking.py` that mixes host observation, lifecycle timing, detector invocation, and public state assembly, and
- tool-specific wrappers in replay and explore paths that bind the current shared reducer to Claude-first flows.

That split creates the wrong architectural center. The most critical logic in this subsystem is the state tracker itself, but it is not currently shaped as a standalone module with a host-neutral API. It is harder than necessary to test with fake time, harder to reuse from non-server hosts, and too easy for server-owned concerns such as tmux probing or response assembly to leak into tracker design.

This change is also constrained by a few explicit requirements from the current exploration:

- the tracker must consume raw TUI strings and derive its own relevant signals,
- the tracker must remain independent of tmux, recorder, and server ownership,
- the tracker must keep one unified contract across supported TUI apps while allowing app-specific implementations,
- the tracker must support versioned signal-detector sets per TUI app, and
- timing should remain internally owned by Rx, while still supporting fake or replayed time through an injected scheduler rather than a wall-clock-only implementation.

## Goals / Non-Goals

**Goals:**

- Create a standalone tracked-TUI module whose core API is independent of `houmao-server`, tmux, recorder artifacts, and snapshot persistence.
- Make the tracker a long-lived reactive session that owns timer-driven state transitions internally through Rx.
- Support both live realtime operation and deterministic replay/fake-time operation through scheduler injection.
- Preserve one shared public tracked-state vocabulary for tracker-owned `surface`, `turn`, `last_turn`, and stability semantics across supported TUI apps.
- Introduce a general plugin/profile contract so Claude Code, Codex, and future TUI apps can plug into the same engine with app-specific signal detection.
- Encapsulate version-specific signal detectors so detector drift can be managed as profile changes rather than as engine rewrites.
- Keep `houmao-server` as a host adapter that combines its own transport/process/parse diagnostics with standalone tracker output.

**Non-Goals:**

- Not rewriting the independent groundtruth/reference paths to stop being independent.
- Not making the standalone tracker responsible for tmux probing, process inspection, parser selection, or snapshot persistence.
- Not removing app-specific detection logic; the goal is to isolate it behind a shared contract, not erase it.
- Not forcing every existing wrapper to migrate in one atomic step without compatibility adapters.
- Not turning the public live server contract back into replay-only observation models or wall-clock-only timing.

## Decisions

### 1. Separate host observation from tracker semantics

**Choice:** The standalone tracker will only own TUI turn-state semantics. Host adapters remain responsible for acquisition and transport concerns such as:

- where raw TUI strings come from,
- whether they came from tmux, recorder files, or another source,
- process and transport diagnostics,
- parser-owned structured surface state for other subsystems,
- lifecycle readiness/completion pipelines for host-owned live/public contracts, and
- server/public response assembly.

The tracker's host-facing inputs are limited to raw snapshot events and explicit input-authority events. Parsed-surface context, transport/process diagnostics, and `LifecycleObservation`-style host lifecycle inputs do not cross the public tracker boundary.

One important first-class raw input shape is direct tmux pane text captured externally by a host adapter. The standalone tracker treats that text as just another raw snapshot string and does not require a tmux-specific wrapper model, normalization step, or capture-side semantic preprocessing before reduction.

**Rationale:** This keeps the tracker general. The state machine should not know whether a string came from tmux, a file, or a future websocket host. It also prevents server- or recorder-shaped models from becoming the default contract for the most reusable part of the system.

**Alternatives considered:**

- Move tmux/process/parse diagnostics into the standalone tracker: rejected because it would make the tracker host-specific again.
- Keep the current blended `record_cycle()` style: rejected because it keeps host orchestration and tracker semantics tangled together.

### 2. Model the tracker as a long-lived Rx session, not a pure timestamped reducer

**Choice:** The standalone module will expose a tracker session object rather than a pure function over timestamped observations.

That session owns:

- Rx subjects for incoming snapshot and input events,
- the selected app/plugin profile,
- the injected scheduler,
- the current tracked state cache, and
- emitted transition events.

The live-facing API stays simple and thread-safe for concurrent producer/reader use:

- `on_snapshot(raw_text: str) -> None`
- `on_input_submitted() -> None`
- `current_state() -> TrackedStateSnapshot`
- `drain_events() -> list[TrackedStateTransition]`

**Rationale:** The tracker itself is stateful and timer-driven. Representing it as a session aligns with the actual problem, keeps the public API free of caller-managed timestamps, and matches the repo's existing successful Rx lifecycle-kernel pattern. Making the public methods thread-safe also matches how server polling and state reads already happen from background workers in the repo.

**Alternatives considered:**

- Keep a replay-style `process_observation(ts=...)` reducer as the primary API: rejected because it leaks timing mechanics into every caller and encourages manual timer reasoning.
- Make the tracker fully stateless and rebuild from history on every call: rejected because it is a poor fit for live operation and timer ownership.

### 3. Keep timer semantics internal, but make the scheduler injectable

**Choice:** The tracker will continue to own settle windows, debounce windows, and other timer-driven transitions internally through Rx timers. It will not require callers to pass timestamps to normal live APIs.

Instead, the time boundary is the injected scheduler:

- live hosts use a realtime scheduler,
- replay and tests use a virtual scheduler,
- replay adapters fake time by scheduling event arrival and/or advancing the injected virtual scheduler.

**Rationale:** This is the most general design. It preserves the clarity of internally owned timing while still allowing deterministic replay and fake-time testing. It also avoids a realtime-only trap.

**Alternatives considered:**

- Require timestamps as input on every tracker event: rejected because it pushes timing mechanics into all callers and weakens the reactive design.
- Use only wall-clock timers: rejected because it would make replay and deterministic testing significantly worse.

### 4. Use a unified app plugin contract with versioned profile resolution

**Choice:** The standalone tracker engine will resolve a supported TUI app through a shared plugin contract:

- `app_id`
- `observed_version`
- exact-match or closest-compatible semver-floor profile resolution
- detection entrypoint returning normalized signals

The engine will not switch behavior through ad hoc tool strings and scattered conditional branches alone. The new shared boundary replaces public `tool == ...` selection, while allowing temporary internal shims during migration. The tracker does not directly depend on parser/backend preset registries such as `VersionedPresetRegistry`; it defines its own tracker-local profile resolution behavior.

**Rationale:** Different TUI apps genuinely have different surfaces, but the tracker contract should still be unified. Plugin/profile resolution lets the engine remain generic while giving app-specific logic a disciplined extension point.

**Alternatives considered:**

- Keep hard-coded `tool == "claude"` / `tool == "codex"` selection as the primary architecture: rejected because it scales poorly and keeps the engine coupled to a fixed tool list.
- Give each app its own tracker engine: rejected because it duplicates timing/state-machine behavior unnecessarily.

### 5. Encapsulate app/version drift as signal-profile composition

**Choice:** Each supported app profile will own a suite of signal detectors rather than one monolithic detector class being the only extensibility boundary.

Examples of profile-owned signal detectors include:

- prompt visibility,
- active-work evidence,
- interrupted signal,
- known-failure signal,
- success-candidate signal,
- ambiguous interactive surface detection.

Detection returns:

- normalized signals consumed by the shared engine, derived from raw snapshot text alone, and
- profile-owned matched-signal detail for tests and debugging.

That matched-signal detail remains an internal/debugging surface in v1 rather than part of the stable `current_state()` contract.

**Rationale:** Version drift usually affects only some signals, not the whole engine. Profile-owned detector suites allow targeted updates when a TUI changes, while keeping the normalized engine contract stable. Keeping detection raw-text-first preserves the standalone boundary instead of carrying parser-shaped host inputs into the tracker.

**Alternatives considered:**

- One giant detector class per app version: rejected because it becomes hard to diff, reuse, and test at signal granularity.
- Push all signal logic into the engine: rejected because app/version drift would then destabilize shared timing logic.

### 6. Keep the official tracked-state vocabulary stable while moving diagnostics out of the tracker

**Choice:** The standalone tracker will continue to output the shared official/runtime tracked-state vocabulary for tracker-owned `surface`, `turn`, `last_turn`, detector identity, and tracker-state stability semantics, but it will not own server transport/process/parse diagnostics or host lifecycle readiness/completion state.

The server adapter will combine:

- host-owned diagnostics and parsed-surface metadata, and
- host-owned lifecycle readiness/completion outputs where those remain part of the live contract, and
- standalone tracker output for `surface`, `turn`, `last_turn`, detector identity, and tracker-owned stability.

The tracker owns stability only over its own emitted state. The server continues to compute effective visible stability when diagnostics or other host-owned fields participate in the published signature.

**Rationale:** The public state contract remains stable for consumers, while the standalone tracker stays general. This also keeps the tracker from becoming another copy of the server's watch-plane model.

**Alternatives considered:**

- Move all server diagnostics into the standalone tracker output: rejected because it would re-couple the tracker to one host architecture.
- Make the tracker output only raw signal reports and let each host define its own turn vocabulary: rejected because it would fragment the consumer-facing state model.

### 7. Migrate through compatibility adapters instead of a flag day

**Choice:** The implementation should initially provide adapters or wrappers so existing server, replay, and explore code can migrate to the new session boundary without every caller being rewritten at once.

Examples:

- wrap old `replay_timeline()` helpers and recorder analyzers around the new tracker session,
- keep temporary detector-selection shims while moving to plugin/profile registration,
- adapt `explore/claude_code_state_tracking` compatibility wrappers and server `record_cycle()` to feed the new tracker before simplifying their surrounding state assembly.

**Rationale:** This subsystem is critical. A staged migration lowers risk and makes regression testing easier.

**Alternatives considered:**

- Rewrite all callers directly to the final API in one step: rejected because it concentrates too much behavioral risk into one change.

## Risks / Trade-offs

- **[More abstraction layers]** → Keep the engine/plugin/adapter boundaries small and explicit, and avoid inventing extra intermediate models that do not carry their weight.
- **[Scheduler misuse could create subtle replay/live mismatches]** → Standardize tracker construction around injected scheduler factories and add deterministic virtual-time tests for timer-sensitive transitions.
- **[Server still needs to combine two state sources]** → Keep the standalone tracker vocabulary narrow and stable so the server merge logic is mechanical rather than policy-heavy.
- **[Profile proliferation across app versions]** → Encourage composition and closest-compatible fallback profiles rather than copying whole detector trees for every version.
- **[Migration may temporarily preserve compatibility shims]** → Treat the shim period as explicit migration work with follow-up cleanup tasks rather than leaving it open-ended.

## Migration Plan

1. Define the standalone tracker contracts, including a thread-safe session API, tracker-owned state/event models, and scheduler injection.
2. Rebuild the current shared tracker around an Rx session with injected scheduler ownership and raw-snapshot-only public inputs.
3. Extract Claude Code and Codex detection into app plugins and versioned raw-text signal profiles with explicit closest-compatible semver-floor resolution.
4. Add compatibility wrappers for current replay-oriented callers, `explore/claude_code_state_tracking`, and recorder analysis/replay paths.
5. Adapt `houmao-server` live tracking to feed the standalone tracker and consume its tracker-owned state while keeping lifecycle readiness/completion and effective visible stability in the server adapter.
6. Update replay, interactive-watch, and terminal-record paths to drive the same tracker through live or virtual schedulers.
7. Remove obsolete replay-shaped or host-coupled tracker APIs once migration coverage is complete.

**Rollback:** Keep the compatibility wrappers and the old host call sites available until the new tracker session proves equivalent under existing unit and replay validation coverage. If migration reveals unacceptable regressions, callers can temporarily remain on the compatibility seam while the standalone engine is corrected.
