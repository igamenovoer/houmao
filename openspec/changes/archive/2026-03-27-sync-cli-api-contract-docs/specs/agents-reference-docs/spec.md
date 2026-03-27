## MODIFIED Requirements

### Requirement: Agent operational documentation covers session lifecycle and message-passing modes

The runtime-managed agent operational documentation SHALL explain how runtime-owned sessions behave across lifecycle actions and message-passing paths using the current public runtime posture.

At minimum, that operational guidance SHALL cover:

- session start, resume, and stop expectations,
- how gateway capability publication fits into the runtime-owned session lifecycle,
- how message passing differs across direct prompt turns, raw control input, mailbox prompt flows, and gateway-routed requests,
- the current support boundary for raw control input in public documentation,
- which flows are synchronous versus queued versus delegated to another subsystem,
- the distinction between current managed-agent workflows and narrower legacy compatibility surfaces.

#### Scenario: Operational guidance reflects current public control surfaces

- **WHEN** a reader needs to understand how to interact with a runtime-managed session
- **THEN** the agent operations pages explain the current managed-agent lifecycle and message-passing modes using current command names and current support boundaries
- **AND THEN** the reader is not told to use stale managed-agent control shapes such as `--session-id` targeting or `agents terminate` as the primary workflow

#### Scenario: Raw control-input guidance matches current posture

- **WHEN** a reader needs to understand raw control input versus prompt turns
- **THEN** the agent operations pages explain the current supported raw control-input paths without presenting deprecated standalone `cao_rest` control as the primary public posture
- **AND THEN** the docs make clear which paths are direct prompt turns, which are exact raw control input, and which require a live gateway
