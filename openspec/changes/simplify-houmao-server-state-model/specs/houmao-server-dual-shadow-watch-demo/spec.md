## MODIFIED Requirements

### Requirement: Monitor SHALL consume Houmao-server tracked state every 0.5 seconds and render a `rich` dashboard
The monitor process SHALL poll each tracked terminal through `houmao-server` every `0.5` seconds.

For each poll, the monitor SHALL consume the authoritative tracked-state payload exposed by `houmao-server` for that terminal. The monitor SHALL NOT require direct CAO terminal-output polling, a demo-local parser stack, or a demo-local lifecycle/state tracker in order to render current live state.

The live monitor session SHALL render a `rich` dashboard that makes it easy to compare both agents side by side while the operator interactively prompts Claude Code and Codex. At minimum, the dashboard SHALL show current server-owned diagnostics, foundational observables (`processing`, `accepting_input`, `editing_input`, and input kind), current work kind and phase, the most recent terminal outcome, and any diagnostic stability or parsed-surface evidence needed for operator validation.

The dashboard SHALL present those simplified server-owned fields as the primary state vocabulary. It SHALL NOT require the operator to interpret the old readiness/completion/authority-heavy lifecycle language in order to understand what each terminal is doing now or what the last cycle did.

The monitor SHALL keep a rolling transition log in the display so an operator can see state changes as they happen rather than only the latest steady-state row.

#### Scenario: Monitor updates current server-owned state on a fixed cadence
- **WHEN** the monitor session is active while the demo is running
- **THEN** it refreshes the displayed state for both agents every `0.5` seconds
- **AND THEN** the dashboard reflects the latest tracked state returned by `houmao-server` for each terminal

#### Scenario: Monitor does not re-derive tracked state locally
- **WHEN** the monitor renders current live state for a tracked terminal
- **THEN** it consumes the server-owned tracked-state payload as the authority
- **AND THEN** it does not run a second parser, lifecycle reducer, or state tracker to decide what state to display

#### Scenario: Monitor presents the simplified work-cycle vocabulary
- **WHEN** an operator watches one tracked terminal move from idle input readiness through active work and back to ready
- **THEN** the dashboard presents that progression through the simplified server-owned surface/work/outcome fields
- **AND THEN** the operator does not need to interpret public `candidate_complete`, `completed`, `stalled`, or turn-authority fields to follow the cycle
