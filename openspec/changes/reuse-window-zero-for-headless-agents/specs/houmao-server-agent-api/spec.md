## ADDED Requirements

### Requirement: Managed headless tmux inspectability keeps the agent in window 0
For managed tmux-backed headless agents, `houmao-server` SHALL treat tmux window 0 of the bound session as the primary agent surface.

Managed headless turn execution SHALL reuse that stable primary surface and SHALL NOT allocate transient per-turn tmux windows as part of normal managed execution.

Additional windows MAY exist in the same tmux session for auxiliary processes or diagnostics, but `houmao-server` SHALL NOT treat those windows as the canonical agent surface and SHALL NOT require callers or demos to chase them in order to watch the agent itself.

Best-effort tmux-facing diagnostics or fallback control paths for managed headless agents SHALL target the stable primary agent surface rather than assuming that the active turn owns a disposable tmux window.

#### Scenario: Managed active turn stays on the stable primary surface
- **WHEN** a caller submits a managed headless prompt that is accepted as the one active turn for that agent
- **THEN** the managed headless execution runs on the session's stable window-0 agent surface
- **AND THEN** `houmao-server` does not create a separate `turn-N` tmux window for that managed turn

#### Scenario: Auxiliary tmux windows do not redefine the managed agent surface
- **WHEN** the tmux session of a managed headless agent also contains another window for gateway, logs, or diagnostics
- **THEN** `houmao-server` continues treating window 0 as the canonical agent surface
- **AND THEN** auxiliary windows do not change managed inspectability or fallback-control targeting for that agent
