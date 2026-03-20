## 1. State Reference Guide

- [ ] 1.1 Create `docs/developer/houmao-server/state-reference.md` with the source-of-truth pointer to `src/houmao/server/models.py`
- [ ] 1.2 Write `diagnostics.availability` section: all five values (`available`, `unavailable`, `tui_down`, `error`, `unknown`) with intuitive meaning, technical derivation, and operational implications
- [ ] 1.3 Write `surface` observables section: `accepting_input`, `editing_input`, `ready_posture` — each with all three tristate values and the three-layer structure
- [ ] 1.4 Write `turn.phase` section: `ready`, `active`, `unknown` with three-layer structure
- [ ] 1.5 Write `last_turn.result` section: `success`, `interrupted`, `known_failure`, `none` with three-layer structure
- [ ] 1.6 Write `last_turn.source` section: `explicit_input`, `surface_inference`, `none` with three-layer structure

## 2. State Transitions and Operations Guide

- [ ] 2.1 Create `docs/developer/houmao-server/state-transitions.md` with introductory context
- [ ] 2.2 Add Mermaid state-flow diagram showing diagnostics → surface → turn → last_turn composition
- [ ] 2.3 Write operation acceptability table for major state combinations: available+ready, available+active, available+unknown, tui_down, unavailable, error
- [ ] 2.4 Write stability and timing guidance section: how `stable_for_seconds` affects operation timing, premature success retraction risk
- [ ] 2.5 Write turn anchor effects section: `explicit_input` vs `surface_inference` timing differences and settle guarantees

## 3. Documentation Structure Revision

- [ ] 3.1 Rewrite `docs/developer/houmao-server/index.md` with three audience-based reading paths (State Reference, Transitions & Operations, Pipeline Architecture)
- [ ] 3.2 Add cross-reference note in `docs/developer/houmao-server/state-tracking.md` Public Contract section pointing to the new state reference guide
- [ ] 3.3 Replace duplicated mapping sections in `docs/migration/houmao/internals/tui_handling/live_state_model.md` with brief summaries + links to new state reference guide (preserve migration-specific content: identity/aliases, initial state, internal timing)

## 4. Review and Verify

- [ ] 4.1 Verify all cross-reference links between docs resolve correctly
- [ ] 4.2 Verify every public enum value from `models.py` appears in the state reference guide
- [ ] 4.3 Verify Mermaid diagrams render correctly in a markdown preview
