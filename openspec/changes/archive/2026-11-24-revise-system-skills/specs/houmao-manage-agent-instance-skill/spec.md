# Agent Instance Skill Delta

## ADDED Requirements

### Requirement: Instance launch guidance resolves one-shot tmux selection
The instance launch workflow SHALL show the supported one-shot `project agents launch` tmux selector. It SHALL explain that a direct selector overrides the saved profile for that birth, while relaunch follows the recorded socket.

#### Scenario: One launch selects a different server from its profile
- **WHEN** a caller wants the shared Houmao server for one launch from a profile that selects a private server
- **THEN** the guidance shows `project agents launch --profile PROFILE --tmux-server houmao-default`
- **AND THEN** it explains that the execution owner's registry-backed shared server starts lazily at its recorded address and the saved profile retains its selector

#### Scenario: One launch selects an existing explicit socket
- **WHEN** the caller chooses `--tmux-server socket`
- **THEN** the guidance pairs it with `--tmux-socket-path` for an absolute path to a running server in the execution owner's context
- **AND THEN** it describes a missing or conflicting socket as a launch failure

#### Scenario: Launch leaves tmux selection to the existing precedence
- **WHEN** the caller leaves selection unspecified
- **THEN** the guidance preserves the saved profile selector or, when absent, uses the existing admitted executor or local scope, enclosing tmux, and native default fallback
- **AND THEN** it distinguishes `user-default`, `houmao-default`, `new`, and `socket` in the selector guidance

### Requirement: Instance skill routes native resource operations
The instance skill SHALL expose a `native-resources` command page for scoped `home`, `refresh --check`, and `refresh`. It SHALL use verified self or an explicitly selected agent within the caller's supported authority, and route authorized logical mount edits to `agent-files`.

#### Scenario: A managed agent asks about native resource freshness
- **WHEN** the verified managed caller needs to read its active native home or observe freshness
- **THEN** the guidance uses `agents self home` or `agents self refresh --check`
- **AND THEN** it explains that check reports common skill and MCP observations without requesting reload
- **AND THEN** it directs native-special-plugin inspection to the body's own facilities

#### Scenario: Native refresh returns a nonterminal or limited result
- **WHEN** scoped refresh reports automatic discovery, partial effects, busy state, or a restart requirement
- **THEN** the skill reports the observed state, native boundary, and result
- **AND THEN** it keeps managed launch-material regeneration and process restart in the separately selected relaunch workflow

#### Scenario: A peer requests a change on a managed mount
- **WHEN** the request concerns editing files on a gateway-owned logical mount
- **THEN** the skill delegates to `agent-files` and carries the selected agent forward
- **AND THEN** it treats the returned native home as diagnostic context
