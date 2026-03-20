## Context

The houmao-server TUI state tracking system exposes a simplified public state model (`HoumaoTerminalStateResponse`) with four consumer-facing groups: `diagnostics`, `surface`, `turn`, and `last_turn`, plus `stability` and `recent_transitions`. The current documentation lives in two locations:

- `docs/developer/houmao-server/` — a maintainer-oriented guide with `index.md` (entry point + source map) and `state-tracking.md` (pipeline, mapping rules, turn anchors, stability).
- `docs/migration/houmao/internals/tui_handling/` — migration notes including `live_state_model.md` (public state shape, initial state, diagnostics/surface/turn mappings) plus pipeline, registration, supervisor, and lifecycle docs.

The two locations overlap significantly (diagnostics mapping, surface observables, turn/last-turn semantics are documented in both) and neither provides a self-contained answer to "what does state X mean and what can I do in it?"

## Goals / Non-Goals

**Goals:**

- Provide a **state reference guide** that a service integrator can read standalone to understand every public state value — its intuitive meaning, what produces it, and what operations make sense when it is active.
- Provide a **state transitions and operations guide** that documents which transitions are valid, what stability/anchoring mean for operation timing, and what a consumer should or should not do in each state.
- Add a **Mermaid state-flow diagram** showing how diagnostics compose into surface, turn, and last-turn.
- Restructure `docs/developer/houmao-server/index.md` to present clear reading paths: quick-reference (state catalog), operator guidance (transitions + operations), and deep-dive (pipeline architecture + internals).
- Eliminate content duplication between developer docs and migration internals by making migration docs point to the new reference docs for state definitions.

**Non-Goals:**

- Rewriting the migration internals wholesale — those remain useful as historical migration context; we only replace duplicated mapping tables with cross-references.
- Documenting the internal reducer graph, ReactiveX kernel internals, or turn-anchor implementation details — those stay in the existing architecture docs.
- Documenting managed headless agent state — that is a separate concern from TUI terminal tracking.
- Changing the public API or models — this is documentation-only.

## Decisions

### D1: Two new docs rather than one monolithic reference

**Decision**: Create two separate new documents — a state reference catalog and a transitions/operations guide — rather than merging everything into the existing `state-tracking.md`.

**Rationale**: The state catalog serves a "what does X mean?" lookup need, while the transitions guide serves a "what should I do when I see X?" workflow need. Keeping them separate allows each to stay focused. The existing `state-tracking.md` retains its role as the architecture deep-dive (pipeline, anchors, settle timing).

**Alternative considered**: Merging all content into `state-tracking.md` with sections. Rejected because it would make the file too long and mix reference lookups with architectural explanation.

### D2: Operator-first structure in the state reference

**Decision**: Each state value entry in the reference guide follows: value name → intuitive meaning (one sentence) → technical derivation (where it comes from in the pipeline) → operational implications (what operations are safe, what to expect next).

**Rationale**: This is the structure the user identified as missing. Operators need the intuitive meaning first, then drill into technical detail only if needed.

### D3: Mermaid diagrams embedded in the transitions doc

**Decision**: Embed Mermaid state diagrams directly in the transitions guide rather than a separate diagram file.

**Rationale**: Diagrams are most useful in context. Separate diagram files require readers to switch between files. GitHub and most markdown renderers handle inline Mermaid well.

### D4: Migration internals get cross-references, not deletion

**Decision**: Replace duplicated mapping tables in `docs/migration/houmao/internals/tui_handling/live_state_model.md` with brief summaries + links to the new reference docs. Keep the migration-specific context (initial state, identity/aliases, internal timing notes) in place.

**Rationale**: Migration docs serve as historical context for the design choices. Deleting them entirely loses that context. But duplicated mapping rules create a maintenance burden and drift risk.

### D5: Restructure index.md with audience-based reading paths

**Decision**: Rewrite `docs/developer/houmao-server/index.md` to present three reading paths: (1) State Reference — for "what does this value mean?", (2) Transitions & Operations — for "what can I do in this state?", (3) Pipeline Architecture — for "how does the tracker build state?" (existing `state-tracking.md`).

**Rationale**: The current index only points to `state-tracking.md` and lacks entry points for the new docs. Audience-based paths help readers find the right doc without reading everything.

## Risks / Trade-offs

- **[Content drift]** The reference docs could drift from `models.py` as code evolves → Mitigation: Include source-of-truth pointers in each doc, and add a note that the canonical definitions live in `models.py`.
- **[Over-documentation]** Adding two docs increases maintenance surface → Mitigation: Keep docs focused on stable public contract (which changes rarely); internal implementation details stay in `state-tracking.md` only.
- **[Cross-reference fragility]** Links between migration docs and new reference docs can break → Mitigation: Use relative paths and verify during review.
