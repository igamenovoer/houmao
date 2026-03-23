## Context

The houmao-server TUI state tracking system exposes a simplified public state model (`HoumaoTerminalStateResponse`) with four consumer-facing groups: `diagnostics`, `surface`, `turn`, and `last_turn`, plus `stability` and `recent_transitions`. The current documentation lives in two locations:

- `docs/developer/houmao-server/` — a maintainer-oriented guide with `index.md` (entry point + source map) and `state-tracking.md` (pipeline, mapping rules, turn anchors, stability).
- `docs/migration/houmao/internals/tui_handling/` — migration notes including `live_state_model.md` (public state shape, initial state, diagnostics/surface/turn mappings) plus pipeline, registration, supervisor, and lifecycle docs.

The two locations overlap significantly (diagnostics mapping, surface observables, turn/last-turn semantics are documented in both) and neither provides a self-contained answer to "what does state X mean and what can I do in it?"

### Recent source changes affecting this design

Three recent changes materially affect documentation scope and source pointers:

1. **Shared TUI tracking extraction** (`0cc7829 feat: extract shared tui tracking core`): Core state types (`Tristate`, `TrackedDiagnosticsAvailability`, `TurnPhase`, `TrackedLastTurnResult`, `TrackedLastTurnSource`, `TransportState`, `ProcessState`, `ParseStatus`) were extracted from `src/houmao/server/models.py` into a new `src/houmao/shared_tui_tracking/models.py` module. The server now re-imports them. Additionally:
   - A `StreamStateReducer` in `shared_tui_tracking/reducer.py` provides replay-grade offline/live reduction with its own state machine that mirrors the server tracker's public contract.
   - Shared helpers in `shared_tui_tracking/public_state.py` (`diagnostics_availability()`, `turn_phase_from_signals()`, `tracked_last_turn_source_from_anchor_source()`) are the canonical mapping logic, used by both the server `LiveSessionTracker` and the `StreamStateReducer`.
   - Turn signal detectors (Claude `ClaudeCodeSignalDetectorV2_1_X`, Codex `CodexTrackedTurnSignalDetector`, fallbacks) were extracted into `shared_tui_tracking/detectors.py`. The server's `tui/turn_signals.py` re-exports from the shared module.

2. **CAO compatibility boundary reset** (in-flight `reset-cao-compat-boundaries`): HTTP routes are being reorganized — CAO compat moves under `/cao/*`, Houmao-native stays under `/houmao/*`. The state endpoint `GET /houmao/terminals/{terminal_id}/state` is already Houmao-native and unaffected, but docs must not reference legacy root-level route shapes.

3. **Managed headless agent state model** (`beb6c72 feat: land houmao-server state model and headless agent API`): The server now also exposes `HoumaoManagedAgentStateResponse` (with `ManagedAgentAvailability`, `HoumaoManagedAgentTurnView`, `HoumaoManagedAgentLastTurnView`) for native headless agents via `GET /houmao/agents/{agent_ref}/state`. While our primary focus is TUI terminal tracking, the shared `TurnPhase` type is aliased as `ManagedAgentTurnPhase` in the server models, meaning both transport paths share the same turn vocabulary.

These changes mean the documentation must:
- Point to `shared_tui_tracking/models.py` (not `server/models.py`) as the canonical home for core state type definitions.
- Reference `shared_tui_tracking/public_state.py` for the authoritative mapping logic rather than describing it as server-internal.
- Acknowledge the two-consumer architecture: `LiveSessionTracker` (live server) and `StreamStateReducer` (replay/offline) both implement the same public state contract.
- Reference `shared_tui_tracking/detectors.py` for detector families and their signal detection logic.
- Use Houmao-native route paths (`/houmao/terminals/{terminal_id}/state`) consistently, not legacy root routes.

## Goals / Non-Goals

**Goals:**

- Provide a **state reference guide** that a service integrator can read standalone to understand every public state value — its intuitive meaning, what produces it, and what operations make sense when it is active. This is the primary "what does state X mean?" document for new developers.
- Provide a **state transitions and operations guide** that is diagram-first: Mermaid statechart diagrams for each state group (`diagnostics.availability`, `turn.phase`, `last_turn.result`) showing all valid transitions, plus a sequence diagram showing a full turn lifecycle from the TUI user's perspective. Prose sections document operation acceptability per state, stability/anchor timing, and reducer priority rules. This is the primary "how do states change and what can I do?" document for new developers.
- Restructure `docs/developer/houmao-server/index.md` to present clear reading paths: quick-reference (state catalog), operator guidance (transitions + operations), and deep-dive (pipeline architecture + internals).
- Eliminate content duplication between developer docs and migration internals by relocating houmao-server internals documentation from `docs/migration/` to `docs/developer/`, leaving migration docs focused on how to transition from CAO to houmao.

**Non-Goals:**

- Rewriting the relocated internals docs themselves — they move as-is (with updated relative paths and source pointers); substantive content revision is a separate concern.
- Documenting the internal reducer graph, ReactiveX kernel internals, or turn-anchor implementation details — those stay in the existing architecture docs.
- Documenting managed headless agent state lifecycle in detail — that is a separate concern. However, the docs must note the shared `TurnPhase` type and clarify that `ManagedAgentTurnPhase` is an alias of the same `TurnPhase` from `shared_tui_tracking`.
- Changing the public API or models — this is documentation-only.
- Full documentation of `StreamStateReducer` replay semantics — the new docs focus on the shared public state contract, not the replay infrastructure.
- Rewriting the migration guide (`server-pair/migration-guide.md`) or tested-scope docs — those remain migration-focused and are already correctly scoped.

## Target Directory Structure

### Before

```
docs/developer/houmao-server/
├── index.md                          # entry point, source map, one reading path
└── state-tracking.md                 # pipeline, mapping rules, turn anchors, stability

docs/migration/houmao/
├── server-pair/
│   ├── README.md                     # what was implemented
│   ├── migration-guide.md            # CAO→houmao transition steps
│   └── tested.md                     # verification scope
└── internals/tui_handling/
    ├── README.md                     # module map, reading order
    ├── registration_and_discovery.md # registration route, storage, enrichment
    ├── probe_parse_track_pipeline.md # poll cycle, transport, process, parser, signals
    ├── supervisor_and_lifecycle.md   # reconcile loop, workers, alias lifecycle
    └── live_state_model.md           # public state shape, mappings (duplicates state-tracking.md)
```

### After

```
docs/developer/houmao-server/
├── index.md                          # REWRITTEN: four audience-based reading paths,
│                                     #   updated Source Of Truth Map with shared_tui_tracking/
├── state-reference.md                # NEW: state value catalog — every public enum value with
│                                     #   compact Mermaid statechart per state group (overview +
│                                     #   link to full diagram); three-layer entries (intuitive →
│                                     #   derivation → operational); architecture note; detector
│                                     #   families; source-of-truth pointers
├── state-transitions.md              # NEW: diagram-first guide for new developers:
│                                     #   1. diagnostics availability statechart (stateDiagram-v2)
│                                     #   2. turn phase statechart (stateDiagram-v2)
│                                     #   3. last-turn result statechart (stateDiagram-v2)
│                                     #   4. turn lifecycle sequence diagram (sequenceDiagram)
│                                     #   5. state composition flowchart (flowchart TD)
│                                     #   then: operation acceptability table, stability/timing
│                                     #   guidance, anchor effects, reducer priority chain
├── state-tracking.md                 # UPDATED: existing pipeline architecture deep-dive;
│                                     #   Public Contract section gains cross-ref to state-reference.md;
│                                     #   source pointers updated to shared_tui_tracking/
└── internals/                        # RELOCATED from docs/migration/houmao/internals/tui_handling/
    ├── README.md                     #   module map, reading order (relative paths updated)
    ├── registration_and_discovery.md #   (relative source paths updated)
    ├── probe_parse_track_pipeline.md #   (relative source paths updated; detector refs → shared_tui_tracking/)
    ├── supervisor_and_lifecycle.md   #   (relative source paths updated)
    └── live_state_model.md           #   DEDUPED: mapping sections → cross-refs to state-reference.md;
                                      #   identity/aliases, initial state, internal timing preserved

docs/migration/houmao/
├── server-pair/
│   ├── README.md                     # UPDATED: reading order points to docs/developer/houmao-server/internals/
│   ├── migration-guide.md            # unchanged
│   └── tested.md                     # unchanged
└── internals/tui_handling/
    └── README.md                     # REDIRECT NOTE only → docs/developer/houmao-server/internals/
```

## Decisions

### D1: Two new docs rather than one monolithic reference

**Decision**: Create two separate new documents — a state reference catalog and a transitions/operations guide — rather than merging everything into the existing `state-tracking.md`.

**Rationale**: The state catalog serves a "what does X mean?" lookup need, while the transitions guide serves a "what should I do when I see X?" workflow need. Keeping them separate allows each to stay focused. The existing `state-tracking.md` retains its role as the architecture deep-dive (pipeline, anchors, settle timing).

**Alternative considered**: Merging all content into `state-tracking.md` with sections. Rejected because it would make the file too long and mix reference lookups with architectural explanation.

### D2: Operator-first structure in the state reference

**Decision**: Each state value entry in the reference guide follows: value name → intuitive meaning (one sentence) → technical derivation (where it comes from in the pipeline) → operational implications (what operations are safe, what to expect next).

**Rationale**: This is the structure the user identified as missing. Operators need the intuitive meaning first, then drill into technical detail only if needed.

### D3: Mermaid diagrams as the primary onboarding tool for new developers

**Decision**: The transitions guide embeds multiple Mermaid diagrams inline (not in separate files). The diagrams are the first thing a new developer should read — they answer "what states exist and how do they relate" before the prose explains details. The required diagrams are:

1. **Diagnostics availability statechart** — a `stateDiagram-v2` showing the five `diagnostics.availability` values and what drives each transition (tmux up/down, process up/down, parse success/failure, probe error). Entry state is `unknown`. Shows that `available` is the only state that enables meaningful surface/turn tracking.

2. **Turn phase statechart** — a `stateDiagram-v2` showing the three `turn.phase` values (`ready`, `active`, `unknown`) and what drives each transition (anchor arming, active evidence, completion settle, diagnostics degradation, ambiguous interactive surface). Entry state is `unknown`.

3. **Last-turn result statechart** — a `stateDiagram-v2` showing the four `last_turn.result` values (`none`, `success`, `interrupted`, `known_failure`) and what drives each transition (settle timer fires, interruption signal detected, failure signal detected, new anchor armed resets to previous). Entry state is `none`. Shows that `last_turn` is sticky — it only changes on terminal outcomes.

4. **Turn lifecycle sequence diagram** — a `sequenceDiagram` showing a typical end-to-end turn from the TUI user's perspective: consumer sends input → server arms anchor → `turn.phase` becomes `active` → agent works → detector sees success candidate → settle timer fires → `last_turn.result` becomes `success` → `turn.phase` becomes `ready`. A second lane shows the interrupted variant.

5. **State composition flowchart** — a `flowchart TD` (already sketched in the existing `state-tracking.md`) showing how low-level probe/process/parse observations compose upward through detectors and reducers into the four public state groups. This diagram is updated from the existing one to reflect `shared_tui_tracking/` as the source of detectors and mapping helpers.

**Rationale**: A new developer joining the project cannot quickly understand the state model from prose tables alone. Statechart diagrams show valid transitions at a glance. The sequence diagram shows the temporal flow of a real turn. Together they answer the two most common onboarding questions: "what states can the system be in?" and "what happens during a turn?" without requiring the reader to mentally simulate the reducer code.

**Alternative considered**: A single combined diagram. Rejected because it would be too dense — `diagnostics`, `turn`, and `last_turn` each have independent transition rules that are clearer when shown separately.

### D4: Relocate internals docs from migration to developer, leave migration focused on CAO→houmao transition

**Decision**: Move the entire `docs/migration/houmao/internals/tui_handling/` subtree into `docs/developer/houmao-server/internals/` (files: `README.md`, `registration_and_discovery.md`, `probe_parse_track_pipeline.md`, `supervisor_and_lifecycle.md`, `live_state_model.md`). Update all relative source-file paths (currently `../../../../../src/...`, will become `../../../../src/...`). Replace the duplicated state-mapping content in `live_state_model.md` with cross-references to the new `state-reference.md`. Leave a redirect note in the old migration location pointing to the new developer home. Update `docs/migration/houmao/server-pair/README.md` reading order to point to the new developer location.

**Rationale**: These docs describe houmao-server internal architecture (registration, probe/parse pipeline, supervisor lifecycle, live state model). They are developer/maintainer documentation, not migration guidance. Keeping them under `docs/migration/` makes them hard to find for developers and creates the false impression that they are migration-specific. The `docs/migration/houmao/server-pair/` docs (README, migration-guide, tested) genuinely describe the CAO→houmao transition and should stay where they are.

**Alternative considered**: Leave in place with cross-references only (original D4). Rejected because the fundamental problem is location — developers looking for houmao-server internals should find them under `docs/developer/houmao-server/`, not under `docs/migration/`.

### D5: Restructure index.md with audience-based reading paths

**Decision**: Rewrite `docs/developer/houmao-server/index.md` to present four reading paths: (1) State Reference — for "what does this value mean?", (2) Transitions & Operations — for "what can I do in this state?", (3) Pipeline Architecture — for "how does the tracker build state?" (existing `state-tracking.md`), (4) Internals — for registration, probe/parse pipeline, supervisor lifecycle, and live state model details (relocated from migration docs).

**Rationale**: The current index only points to `state-tracking.md`. The relocated internals docs need an entry point alongside the new reference docs. Four paths cover the full audience spectrum: quick lookup → operator workflow → architecture → implementation details.

### D6: Source-of-truth pointers reflect the shared module extraction

**Decision**: The state reference guide points to `src/houmao/shared_tui_tracking/models.py` as the canonical home for core state type definitions, and `src/houmao/shared_tui_tracking/public_state.py` for the authoritative mapping functions. `src/houmao/server/models.py` is documented as the re-export surface for server-specific Pydantic models that consume those types.

**Rationale**: The recent extraction (`0cc7829`) moved the type definitions out of the server into a shared module used by both the live tracker and the offline replay reducer. Pointing to the server models alone would be misleading — a developer modifying the type definitions or mapping logic needs to find `shared_tui_tracking/`, not `server/models.py`.

**Alternative considered**: Pointing only to `server/models.py` since that's where consumers import from. Rejected because it obscures the actual definition site and the shared nature of the contract.

### D7: Acknowledge the two-consumer architecture without over-documenting replay

**Decision**: The state reference guide includes a brief "Architecture Note" section explaining that the public state contract is implemented by two consumers: `LiveSessionTracker` (live server polling) and `StreamStateReducer` (replay/offline). The reference guide defines the shared state vocabulary; implementation-specific behavior (settle timers, anchor lifecycle) is deferred to the existing `state-tracking.md` and replay docs.

**Rationale**: Users reading the reference guide need to know the state definitions aren't server-specific — the same values appear in replay timelines. But the reference guide should not become a replay reducer manual.

### D8: Detector families documented as part of state derivation

**Decision**: The state reference guide includes a brief section explaining that surface observables (`accepting_input`, `editing_input`, `ready_posture`) and signal evidence (`active_evidence`, `interrupted`, `known_failure`, `success_candidate`) are produced by tool-specific detectors in `shared_tui_tracking/detectors.py`. The section lists the three detector families (Claude `2.1.x`, Codex `app_server`, Fallback) and their selection logic without reproducing the full detection rules.

**Rationale**: Without this, users cannot understand why the same `ready_posture=yes` might mean different things for Claude vs Codex, or why `unknown` is more common with unsupported tools. The existing docs mention detectors obliquely but never name the families or explain the selection.

### D9: Use Houmao-native route paths consistently

**Decision**: All route references in the new docs use Houmao-native paths (`/houmao/terminals/{terminal_id}/state`, `/houmao/terminals/{terminal_id}/history`, `/houmao/terminals/{terminal_id}/input`) and never reference legacy root-level CAO-compatible paths.

**Rationale**: The in-flight `reset-cao-compat-boundaries` change is moving CAO compatibility under `/cao/*`. New documentation should not introduce references to routes that are being deprecated.

## Risks / Trade-offs

- **[Content drift]** The reference docs could drift from `shared_tui_tracking/models.py` as code evolves → Mitigation: Include source-of-truth pointers in each doc, and add a note that the canonical definitions live in `shared_tui_tracking/models.py`.
- **[Over-documentation]** Adding two docs increases maintenance surface → Mitigation: Keep docs focused on stable public contract (which changes rarely); internal implementation details stay in `state-tracking.md` only.
- **[Cross-reference fragility]** Links between migration docs and new reference docs can break → Mitigation: Use relative paths and verify during review.
- **[Shared module still evolving]** The `shared_tui_tracking` extraction is recent and may see further refactoring → Mitigation: Reference module names and function names rather than line numbers; verify source pointers at implementation time.
- **[Route path churn]** The CAO compat boundary reset is in-flight → Mitigation: Use only `/houmao/*` paths which are stable regardless of the compat reset outcome.
