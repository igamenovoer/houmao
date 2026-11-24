# Agent Messaging Skill Delta

## ADDED Requirements

### Requirement: Messaging separates agent selectors from transport overrides
The messaging skill SHALL select a peer with `agents single --agent-id ID` or `--agent-name NAME` and use `agents self` only for verified current-session scope. It SHALL describe `--port` and `--pair-port` as transport options on the commands that accept them.

#### Scenario: The caller supplies a port but no selected agent
- **WHEN** a caller asks to prompt a peer and gives only a passive server port
- **THEN** the skill asks for the peer identity
- **AND THEN** it retains the supplied port as a transport option for the selected command

## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-messaging` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-messaging` as a parent-scoped child of `houmao-shared-routines`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That skill SHALL instruct agents to communicate with already-existing Houmao-managed agents through these scoped manager and HTTP surfaces:

- `agents single ... state` or verified `agents self state`
- scoped `gateway status`, `mail resolve-live`, `prompt`, and `interrupt`
- scoped `gateway prompt|interrupt|send-keys`
- scoped `gateway tui state|history|note-prompt`
- managed-agent HTTP routes under `/houmao/agents/*`

The child `SKILL-MAIN.md` SHALL route to one local action-specific document for `discover`, `prompt`, `interrupt`, `gateway-queue`, `send-keys`, `mail`, or `reset-context`. The catalog and skill SHALL expose `mail` as the canonical handoff command and `mail-handoff` as its alias.

That packaged skill SHALL remain the canonical Houmao-owned skill for communication with already-running managed agents whether the caller is another managed agent or an external operator.

That packaged skill SHALL delegate the following operations to their owning routines:

- managed-agent launch, join, stop, relaunch, and cleanup
- project specialist and project agent authoring and lifecycle commands
- ordinary mailbox status, reads, writes, and archive
- filesystem or Stalwart mailbox transport internals
- gateway attach and detach

#### Scenario: Installed skill points the agent at supported communication surfaces
- **WHEN** an agent opens the installed `houmao-agent-messaging` skill through its parent
- **THEN** the skill directs the agent to the supported prompt, interrupt, gateway, mailbox-discovery, and managed-agent HTTP surfaces

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** `SKILL-MAIN.md` directs the agent to the local document for the requested action
- **AND THEN** `mail` and `mail-handoff` select the same mailbox handoff document

#### Scenario: Installed skill keeps lifecycle and mailbox-operation internals out of scope
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** it delegates managed-agent lifecycle, ordinary mailbox work, and mailbox transport internals
