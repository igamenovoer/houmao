## Why

The houmao-server TUI state tracking system has comprehensive internal documentation spread across `docs/developer/houmao-server/` and `docs/migration/houmao/internals/tui_handling/`, but neither location is structured for the two audiences that need it most:

1. **Service integrators / TUI operators** who poll the `/houmao/terminals/{terminal_id}/state` endpoint and need to know what each state value means, what operations are safe in each state, and how to interpret transitions — without reading implementation internals.
2. **Developers extending the tracking system** who need a single-entry-point reference covering state enums, transition rules, and signal-detection contracts — not scattered across migration notes. Recent extraction of core state types and detectors into `shared_tui_tracking/` makes this even more important, as the canonical definitions now live outside the server module.

The current docs explain *how the pipeline works* (poll/parse/reduce) thoroughly but never provide a standalone **state catalog** that defines each enum value with its intuitive meaning, its technical derivation, and the operational implications (what you can/should do when you see it). Migration internals duplicate parts of the developer docs without clear audience separation.

## What Changes

- Introduce a **state reference guide** that catalogs every public state value (diagnostics availability, transport/process state, surface observables, turn phase, last-turn outcome) with intuitive definitions, technical derivation, and operational implications.
- Introduce a **state transitions and operations guide** that documents valid transitions, what operations are acceptable in each state, and how stability/anchoring affect operation timing.
- Restructure `docs/developer/houmao-server/` to separate *reference material* (state catalog, transitions) from *architecture explanation* (pipeline, lifecycle).
- Add a **visual state-flow diagram** (Mermaid) showing how low-level diagnostics compose into surface observables, turn phase, and last-turn outcome.
- Consolidate and cross-reference with migration internals to eliminate content duplication.
- **Relocate** the TUI handling internals docs (`registration_and_discovery.md`, `probe_parse_track_pipeline.md`, `supervisor_and_lifecycle.md`, `live_state_model.md`) from `docs/migration/houmao/internals/tui_handling/` to `docs/developer/houmao-server/internals/`, leaving migration docs focused on the CAO→houmao transition story.

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
- **Files relocated**: `docs/migration/houmao/internals/tui_handling/{README.md,registration_and_discovery.md,probe_parse_track_pipeline.md,supervisor_and_lifecycle.md,live_state_model.md}` → `docs/developer/houmao-server/internals/`. A redirect note left at the old location.
- **Migration docs updated**: `docs/migration/houmao/server-pair/README.md` reading order updated to point to new developer location. Migration docs retain CAO→houmao transition focus only.
- **Cross-references updated**: Relocated `live_state_model.md` will have duplicated mapping sections replaced with links to the new state reference guide.
- **Source pointers updated**: Docs will reference `src/houmao/shared_tui_tracking/models.py` (canonical type definitions), `src/houmao/shared_tui_tracking/public_state.py` (mapping logic), and `src/houmao/shared_tui_tracking/detectors.py` (signal detectors) as the primary source-of-truth, since the recent extraction (`0cc7829`) moved these out of `src/houmao/server/models.py`.
- **Route references**: All docs will use Houmao-native `/houmao/*` paths, aligned with the in-flight `reset-cao-compat-boundaries` change.
- **No code changes** — this is purely a documentation revision.
- **No API changes** — the public state model is unchanged; only its documentation and source pointers are updated.
