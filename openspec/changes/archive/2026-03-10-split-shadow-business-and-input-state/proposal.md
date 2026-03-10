## Why

The current shadow parser contract collapses two different questions into one state model: whether the tool is doing work, and whether the current surface accepts generic user input. That collapse makes the model unable to represent real TUI behavior in Claude Code and Codex, where a session may still be actively working while the prompt remains typeable, and it makes downstream readiness and completion logic reason over a lossy state.

## What Changes

- **BREAKING**: Replace the shared shadow surface contract of `activity + accepts_input` with an orthogonal state model that separates provider business state from input availability.
- Redefine parser-facing readiness as a derived condition over the new axes instead of a primitive parser state.
- Update Claude and Codex shadow parsing requirements so provider contracts can represent `working but typeable`, `gated modal prompt`, and `closed/non-inputtable` surfaces without forcing them into the same bucket.
- Update runtime turn-monitor requirements so prompt submission, completion, blocked handling, and unknown/stalled handling are driven by derived predicates over the corrected state model.
- Explicitly defer transport-quiescence and RxPY refactors until after the shared state contract is corrected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `versioned-shadow-parser-stack`: Change the shared `SurfaceAssessment` contract from a one-dimensional activity model with `accepts_input` into a two-axis business/input model with derived readiness semantics.
- `cao-claude-code-output-extraction`: Change Claude shadow state requirements so Claude can represent working, gated, and input-open surfaces independently instead of forcing `working => accepts_input=false`.
- `cao-codex-output-extraction`: Change Codex shadow state requirements so Codex can represent working, gated, and input-open surfaces independently instead of forcing `working => accepts_input=false`.
- `brain-launch-runtime`: Change `shadow_only` runtime readiness/completion/blocking semantics to consume the corrected two-axis surface contract and derived readiness predicates.

## Impact

- Affected code: `src/gig_agents/agents/brain_launch_runtime/backends/shadow_parser_core.py`, provider parsers for Claude and Codex, and runtime lifecycle logic in `src/gig_agents/agents/brain_launch_runtime/backends/cao_rest.py`.
- Affected docs/specs: shared TUI parsing contracts, provider state docs, and runtime lifecycle docs.
- Affected tests: shared parser contract fixtures, provider parser fixtures, and shadow-mode runtime lifecycle tests.
- Dependencies: no new library dependency is required for this change; the work focuses on correcting contracts and state modeling first.
