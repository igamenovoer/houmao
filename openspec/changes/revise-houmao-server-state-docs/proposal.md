## Why

The houmao-server TUI state tracking system has comprehensive internal documentation spread across `docs/developer/houmao-server/` and `docs/migration/houmao/internals/tui_handling/`, but neither location is structured for the two audiences that need it most:

1. **Service integrators / TUI operators** who poll the `/terminals/{id}/state` endpoint and need to know what each state value means, what operations are safe in each state, and how to interpret transitions — without reading implementation internals.
2. **Developers extending the tracking system** who need a single-entry-point reference covering state enums, transition rules, and signal-detection contracts — not scattered across migration notes.

The current docs explain *how the pipeline works* (poll/parse/reduce) thoroughly but never provide a standalone **state catalog** that defines each enum value with its intuitive meaning, its technical derivation, and the operational implications (what you can/should do when you see it). Migration internals duplicate parts of the developer docs without clear audience separation.

## What Changes

- Introduce a **state reference guide** that catalogs every public state value (diagnostics availability, transport/process state, surface observables, turn phase, last-turn outcome) with intuitive definitions, technical derivation, and operational implications.
- Introduce a **state transitions and operations guide** that documents valid transitions, what operations are acceptable in each state, and how stability/anchoring affect operation timing.
- Restructure `docs/developer/houmao-server/` to separate *reference material* (state catalog, transitions) from *architecture explanation* (pipeline, lifecycle).
- Add a **visual state-flow diagram** (Mermaid) showing how low-level diagnostics compose into surface observables, turn phase, and last-turn outcome.
- Consolidate and cross-reference with migration internals to eliminate content duplication.

## Capabilities

### New Capabilities
- `state-reference-guide`: A standalone catalog of all public TUI state enums/values with intuitive meaning, technical derivation, and operational implications (what operations are safe/expected in each state).
- `state-transitions-and-ops`: Documents valid state transitions, operation acceptability per state, stability windows, and turn-anchoring effects on operation timing.
- `docs-structure-revision`: Restructured `docs/developer/houmao-server/` index and reading paths for operator vs developer audiences, with Mermaid state-flow diagram and cross-references to migration internals.

### Modified Capabilities
<!-- No existing openspec specs are affected; this is a documentation-only change. -->

## Impact

- **Files modified**: `docs/developer/houmao-server/index.md`, `docs/developer/houmao-server/state-tracking.md` (restructured, content moved out to new docs).
- **Files created**: New state reference guide, state transitions/operations guide, Mermaid diagram file or embedded diagrams.
- **Cross-references updated**: `docs/migration/houmao/internals/tui_handling/live_state_model.md` will gain forward-pointers to the new reference docs instead of duplicating mapping tables.
- **No code changes** — this is purely a documentation revision.
- **No API changes** — the public state model in `src/houmao/server/models.py` is unchanged.
