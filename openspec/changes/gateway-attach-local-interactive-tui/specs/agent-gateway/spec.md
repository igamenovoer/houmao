## MODIFIED Requirements

### Requirement: Gateway execution adapters support REST-backed, local-headless, and server-managed targets
The gateway SHALL execute accepted terminal-mutating request kinds through an explicit execution-adapter boundary selected from durable attach metadata and manifest-backed runtime authority.

In this change, the gateway execution layer SHALL support at minimum:

- a direct REST-backed terminal adapter for the existing runtime-owned REST-backed sessions,
- a local tmux-backed adapter for runtime-owned native headless sessions and runtime-owned `local_interactive` sessions outside `houmao-server`, and
- a server-managed-agent adapter for managed-agent execution owned by `houmao-server`.

For server-managed agents, the gateway SHALL submit prompt and interrupt work through the server-owned managed-agent API rather than locally resuming the session and bypassing server-owned turn or interrupt authority.

The gateway SHALL preserve the same durable queueing, serialization, and admission semantics regardless of which execution adapter is selected.

#### Scenario: Gateway prompt for a server-managed headless agent flows through `houmao-server`
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a server-managed native headless agent
- **THEN** the gateway delivers that work through the server-owned managed-agent API
- **AND THEN** the gateway does not bypass server-owned headless turn authority by privately resuming the managed session itself

#### Scenario: Gateway prompt for a runtime-owned headless session uses the local tmux-backed adapter
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a runtime-owned native headless session outside `houmao-server`
- **THEN** the gateway uses the local tmux-backed execution adapter for that session
- **AND THEN** the gateway still preserves its durable request queue and single active execution slot semantics

#### Scenario: Gateway prompt for a runtime-owned local interactive session uses the local tmux-backed adapter
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a runtime-owned `local_interactive` session outside `houmao-server`
- **THEN** the gateway uses the local tmux-backed execution adapter for that session
- **AND THEN** prompt delivery targets the live provider TUI through the gateway-owned queue rather than bypassing the gateway path

#### Scenario: Gateway interrupt for a runtime-owned local interactive session uses the local tmux-backed adapter
- **WHEN** a live gateway executes an accepted `interrupt` request for a runtime-owned `local_interactive` session outside `houmao-server`
- **THEN** the gateway uses the local tmux-backed execution adapter for that session
- **AND THEN** interrupt delivery targets the live provider TUI through the gateway path rather than bypassing the gateway with direct concurrent control

#### Scenario: Existing REST-backed gateway execution remains supported
- **WHEN** a live gateway executes an accepted request for an existing runtime-owned REST-backed session
- **THEN** the gateway may continue using the direct REST-backed execution adapter for that session
- **AND THEN** adding local tmux-backed or server-managed adapters does not require the REST-backed path to change its public request semantics
