# Spec Delta

## MODIFIED Requirements

### Requirement: Gateway execution adapters support REST-backed, local-headless, and server-managed targets
The gateway SHALL execute accepted terminal-mutating request kinds through an explicit execution-adapter boundary selected from durable attach metadata and manifest-backed runtime authority. The gateway SHALL bind managed work to the recorded run mode, current owner generation, and supported operations before dispatch. A supervisor pane or reachable listener alone SHALL NOT authorize a fallback adapter.

In this change, the gateway execution layer SHALL support at minimum:

- a direct REST-backed terminal adapter for the existing runtime-owned REST-backed sessions,
- a local tmux-backed adapter for runtime-owned native headless and `local_interactive` sessions,
- a structured native adapter for the existing `dsh_web` owner, and
- a passive-server backing adapter for headless execution admitted by `houmao-passive-server`.

For passive-server-owned headless agents, the gateway SHALL submit prompt and interrupt work through the admitted passive backing API so both surfaces preserve a single turn authority. Retained REST-backed sessions continue to use their saved authority.

The gateway SHALL preserve the same durable queueing, serialization, and admission semantics regardless of which execution adapter is selected.

#### Scenario: Gateway prompt for a server-managed headless agent flows through `houmao-server`
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a server-managed native headless agent
- **THEN** the gateway delivers that work through the admitted passive backing API
- **AND THEN** the gateway preserves the passive server's managed headless turn authority

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

#### Scenario: Detached owner refuses stale control

- **WHEN** a gateway holds an execution handle from before owner replacement
- **THEN** the gateway rejects dispatch on that handle and resolves the current owner before accepting more work
