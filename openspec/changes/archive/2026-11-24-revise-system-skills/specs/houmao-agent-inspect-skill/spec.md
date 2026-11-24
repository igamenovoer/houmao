# Agent Inspect Skill Delta

## ADDED Requirements

### Requirement: Inspection separates agent selectors from transport overrides
The inspect skill SHALL use `agents single --agent-id ID` or `--agent-name NAME` for explicit selected-agent commands and verified `agents self` for current-session commands. When showing `--port` or `--pair-port`, it SHALL present the supported option as a transport override that still requires an explicit selected-agent identity.

#### Scenario: A named target uses an explicit passive server
- **WHEN** a caller supplies the name of a peer and an explicit transport port
- **THEN** the skill includes the target name in selected-agent scope
- **AND THEN** it uses the port only with the subordinate command that supports that option

## MODIFIED Requirements

### Requirement: `houmao-agent-inspect` routes inspection through a supported evidence ladder
The packaged `houmao-agent-inspect` skill SHALL tell the caller to recover omitted target selectors from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess a missing required target, transport kind, or inspection lane that is not explicit in current or recent conversation context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL route generic managed-agent inspection in this order:

1. identify the target through scoped manager discovery or an explicit selector
2. read summary state through the scoped manager state command or the matching managed-agent `/state` route
3. consult managed transport detail and gateway observations when available and needed
4. inspect mailbox posture, logs, or runtime artifacts according to the requested domain
5. use a direct local tmux capture only when the actual pane is needed or the managed observations are insufficient

When the caller is already operating through the pair-managed HTTP seam, the skill SHALL allow the matching managed-agent `/houmao/agents/*` inspection routes. Generic discovery and supported record-backed inspection SHALL remain available without a live gateway.

#### Scenario: Missing target requires a user question
- **WHEN** the selected inspection action still lacks a required managed-agent selector after checking the current prompt and recent chat context
- **THEN** the skill tells the caller to ask the user for the missing selector before proceeding

#### Scenario: Generic inspection starts from summary state rather than raw tmux
- **WHEN** a caller asks what one managed agent is doing right now
- **THEN** the skill directs the caller to inspect scoped manager state or the matching managed-agent `/state` route first

#### Scenario: Pair-managed callers may use the detailed managed-agent route
- **WHEN** a caller is already operating through pair-managed HTTP control for one managed agent
- **THEN** the skill allows `GET /houmao/agents/{agent_ref}/state/detail` for transport-specific detail directly

#### Scenario: A detached gateway leaves supported observations available
- **WHEN** a caller asks for a peer's status and the peer has no attached gateway
- **THEN** the skill uses the available managed state and saved records and reports any observation limits

### Requirement: `houmao-agent-inspect` treats TUI and headless inspection differently
The inspect skill SHALL use managed state and detailed state to identify the agent's transport. For TUI tracking it SHALL prefer gateway TUI observations when available. For headless work it SHALL use managed turn state and logs. Direct local tmux capture SHALL require an authoritative recorded socket and exact target in an accessible execution-owner context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

A direct local tmux capture SHALL specify the verified socket and pane. An explicitly requested attach SHALL use a verified socket-qualified handoff command or specify the socket and selected session. The fallback SHALL use the selected owner's exact server even when the caller is inside another server. The fallback SHALL report an unavailable exact target when that socket or target cannot be verified.

#### Scenario: TUI inspection prefers live gateway tracker state when available
- **WHEN** a caller asks to inspect the live tracked TUI state for one managed TUI agent and that agent currently has a healthy live gateway
- **THEN** the skill directs the caller to scoped `gateway tui state|history|watch` or the matching managed-agent gateway TUI routes for the requested evidence

#### Scenario: TUI raw pane peeking stays a local last-resort lane
- **WHEN** a caller explicitly asks to peek the actual local tmux pane for one TUI-backed managed agent
- **THEN** the skill uses managed records to verify the exact socket and pane in the execution owner's context
- **AND THEN** it shows direct capture with `tmux -S SOCKET capture-pane ... -t PANE` after managed observations
- **AND THEN** it reserves attach for an explicit request to attach

#### Scenario: Headless inspection uses managed detail and turn evidence
- **WHEN** a caller asks whether one managed headless agent is idle, active, or failed
- **THEN** the skill directs the caller to managed-agent detailed state and headless turn status or artifact surfaces
