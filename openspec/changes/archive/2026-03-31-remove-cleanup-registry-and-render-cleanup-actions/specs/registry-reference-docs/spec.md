## MODIFIED Requirements

### Requirement: Shared-registry operational documentation covers discovery fallback and cleanup workflows
The shared-registry operational documentation SHALL explain how registry-backed discovery and cleanup behave in the implemented v1 flow.

At minimum, that operational guidance SHALL cover:

- when name-based control uses tmux-local discovery first,
- when shared-registry fallback applies for missing or stale tmux discovery pointers,
- which validation failures still fail fast instead of falling back silently,
- how `houmao-mgr admin cleanup registry` removes stale directories and reports planned, applied, blocked, and preserved cleanup actions,
- how operators should interpret fresh, stale, malformed, and conflicted registry state at the level needed to use the system safely.

#### Scenario: Operational guidance explains name-based resolution fallback
- **WHEN** an operator or developer needs to understand why a name-addressed control action recovered from tmux-local discovery failure
- **THEN** the registry operations pages explain the resolution order and fallback behavior
- **AND THEN** the reader can tell which discovery problems are fallback-eligible and which remain explicit errors

#### Scenario: Operational guidance explains cleanup outcomes
- **WHEN** an operator runs `houmao-mgr admin cleanup registry` or needs to inspect stale registry state
- **THEN** the registry operations pages explain the cleanup grace period, removal behavior, and per-action cleanup reporting for planned, applied, blocked, and preserved outcomes
- **AND THEN** the reader can distinguish currently live entries from stale or cleanup-blocked directories without relying on the retired `cleanup-registry` spelling
