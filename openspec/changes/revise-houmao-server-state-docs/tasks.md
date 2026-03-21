## 1. State Reference Guide

- [ ] 1.1 Create `docs/developer/houmao-server/state-reference.md` with source-of-truth pointers to `src/houmao/shared_tui_tracking/models.py` (type definitions), `src/houmao/shared_tui_tracking/public_state.py` (mapping logic), and `src/houmao/server/models.py` (Pydantic response models)
- [ ] 1.2 Write architecture note: two-consumer contract (`LiveSessionTracker` + `StreamStateReducer`), and clarify `ManagedAgentTurnPhase` is an alias of `TurnPhase` from `shared_tui_tracking`
- [ ] 1.3 Write detector families section: list `claude_code 2.1.x`, `codex_app_server`, `unsupported_tool` fallback; explain selection logic from `shared_tui_tracking/detectors.py`; note that different tools yield different `unknown` distributions
- [ ] 1.4 Write `diagnostics.availability` section: compact Mermaid `stateDiagram-v2` overview (all five values with brief transition labels, link to full diagram in state-transitions.md), then per-value entries with three-layer structure (intuitive → derivation → operational)
- [ ] 1.5 Write `surface` observables section: `accepting_input`, `editing_input`, `ready_posture` — each with all three tristate values and the three-layer structure, noting these are detector-produced
- [ ] 1.6 Write `turn.phase` section: compact Mermaid `stateDiagram-v2` overview (unknown/ready/active with transition labels, link to full diagram), then per-value entries with three-layer structure
- [ ] 1.7 Write `last_turn.result` section: compact Mermaid `stateDiagram-v2` overview (none/success/interrupted/known_failure with transition labels, link to full diagram), then per-value entries with three-layer structure
- [ ] 1.8 Write `last_turn.source` section: `explicit_input`, `surface_inference`, `none` with three-layer structure

## 2. State Transitions and Operations Guide

- [ ] 2.1 Create `docs/developer/houmao-server/state-transitions.md` with introductory context explaining this is the diagram-first guide for understanding state transitions
- [ ] 2.2 Add Mermaid `stateDiagram-v2` for `diagnostics.availability`: all five values as states, labeled transitions showing what drives each (tmux up/down, process start/stop, parse success/failure, probe error); entry state `unknown`; visually highlight `available` as the gateway to meaningful tracking
- [ ] 2.3 Add Mermaid `stateDiagram-v2` for `turn.phase`: three values as states, labeled transitions (anchor arming, active evidence, completion settle, diagnostics degradation, ambiguous interactive surface); entry state `unknown`
- [ ] 2.4 Add Mermaid `stateDiagram-v2` for `last_turn.result`: four values as states, labeled transitions (settle timer fires, interruption signal, failure signal); entry state `none`; show sticky nature and success retraction path
- [ ] 2.5 Add Mermaid `sequenceDiagram` for turn lifecycle: Consumer → Server API → LiveSessionTracker → Detector; show successful turn (input → anchor → active → success_candidate → settle → success → ready) and interrupted variant as alt branch
- [ ] 2.6 Add Mermaid `flowchart TD` for state composition: probe → process → parse → detect (`shared_tui_tracking/detectors.py`) → reduce (`shared_tui_tracking/public_state.py`) → public state groups; update from existing `state-tracking.md` flowchart to reflect shared module
- [ ] 2.7 Write operation acceptability table for major state combinations using Houmao-native routes, placed after all diagrams
- [ ] 2.8 Write stability and timing guidance section: `stable_for_seconds`, premature success retraction, settle window behavior
- [ ] 2.9 Write turn anchor effects section: `explicit_input` vs `surface_inference` timing differences
- [ ] 2.10 Write reducer transition rules section: priority chain (diagnostics → interrupted → known_failure → active_evidence → success_candidate → default), success timer arming/cancellation, surface inference arming

## 3. Relocate Internals from Migration to Developer

- [ ] 3.1 Create `docs/developer/houmao-server/internals/` directory
- [ ] 3.2 Move `docs/migration/houmao/internals/tui_handling/{README.md,registration_and_discovery.md,probe_parse_track_pipeline.md,supervisor_and_lifecycle.md,live_state_model.md}` to `docs/developer/houmao-server/internals/`
- [ ] 3.3 Update all relative source-file paths in relocated files (from `../../../../../src/` to `../../../../src/`)
- [ ] 3.4 Deduplicate `live_state_model.md`: replace diagnostics mapping, surface observables, and turn/last-turn mapping sections with brief summaries + links to `state-reference.md`; preserve identity/aliases, initial state, internal timing sections
- [ ] 3.5 Update `shared_tui_tracking/` source pointers in relocated files where applicable (detectors, turn_signals)
- [ ] 3.6 Leave redirect note at `docs/migration/houmao/internals/tui_handling/README.md` pointing to new developer location
- [ ] 3.7 Update `docs/migration/houmao/server-pair/README.md` reading order to point to `docs/developer/houmao-server/internals/`

## 4. Documentation Structure Revision

- [ ] 4.1 Rewrite `docs/developer/houmao-server/index.md` with four audience-based reading paths (State Reference, Transitions & Operations, Pipeline Architecture, Internals) and updated Source Of Truth Map including `shared_tui_tracking/` modules
- [ ] 4.2 Add cross-reference note in `docs/developer/houmao-server/state-tracking.md` Public Contract section pointing to the new state reference guide; update source pointers to `shared_tui_tracking/`; note that the composition flowchart is now maintained in `state-transitions.md`
- [ ] 4.3 Verify all route references use Houmao-native `/houmao/*` paths

## 5. Review and Verify

- [ ] 5.1 Verify all cross-reference links between docs resolve correctly (especially relocated internals paths)
- [ ] 5.2 Verify every public enum value from `shared_tui_tracking/models.py` appears in the state reference guide
- [ ] 5.3 Verify all five Mermaid diagrams render correctly in a markdown preview (three statecharts, one sequence, one flowchart)
- [ ] 5.4 Verify compact overview diagrams in state-reference.md link to corresponding full diagrams in state-transitions.md
- [ ] 5.5 Verify no houmao-server internals docs remain under `docs/migration/` (only redirect note)
- [ ] 5.6 Verify source-of-truth pointers in all docs reference the correct modules
