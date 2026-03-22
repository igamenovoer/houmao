## ADDED Requirements

### Requirement: Gateway execution adapters support REST-backed, local-headless, and server-managed targets
The gateway SHALL execute accepted terminal-mutating request kinds through an explicit execution-adapter boundary selected from durable attach metadata and manifest-backed runtime authority.

In this change, the gateway execution layer SHALL support at minimum:

- a direct REST-backed terminal adapter for the existing runtime-owned REST-backed sessions,
- a local-headless adapter for runtime-owned native headless sessions outside `houmao-server`, and
- a server-managed-agent adapter for managed-agent execution owned by `houmao-server`.

For server-managed agents, the gateway SHALL submit prompt and interrupt work through the server-owned managed-agent API rather than locally resuming the session and bypassing server-owned turn or interrupt authority.

The gateway SHALL preserve the same durable queueing, serialization, and admission semantics regardless of which execution adapter is selected.

#### Scenario: Gateway prompt for a server-managed headless agent flows through `houmao-server`
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a server-managed native headless agent
- **THEN** the gateway delivers that work through the server-owned managed-agent API
- **AND THEN** the gateway does not bypass server-owned headless turn authority by privately resuming the managed session itself

#### Scenario: Gateway prompt for a runtime-owned headless session uses the local headless adapter
- **WHEN** a live gateway executes an accepted `submit_prompt` request for a runtime-owned native headless session outside `houmao-server`
- **THEN** the gateway uses the local headless execution adapter for that session
- **AND THEN** the gateway still preserves its durable request queue and single active execution slot semantics

#### Scenario: Existing REST-backed gateway execution remains supported
- **WHEN** a live gateway executes an accepted request for an existing runtime-owned REST-backed session
- **THEN** the gateway may continue using the direct REST-backed execution adapter for that session
- **AND THEN** adding headless or server-managed adapters does not require the REST-backed path to change its public request semantics

### Requirement: Gateway status remains meaningful for headless sessions without TUI parsing
For headless sessions, the gateway SHALL derive execution eligibility and request-admission behavior from managed-agent execution posture rather than from parsed TUI surface classification.

The published gateway status contract SHALL remain structurally stable across transports, but headless sessions SHALL NOT require parser-owned or prompt-surface evidence in order to report whether prompt execution is currently eligible.

#### Scenario: Idle headless session reports prompt eligibility without TUI parser state
- **WHEN** a live gateway targets a managed headless session that is available and not currently running a turn
- **THEN** the gateway status reports prompt execution as eligible according to headless execution posture
- **AND THEN** the gateway does not need a parsed terminal-ready surface in order to report that eligibility

#### Scenario: Active headless turn blocks new prompt execution
- **WHEN** a live gateway targets a managed headless session that already has one active managed turn
- **THEN** the gateway status reports non-open prompt admission for that session
- **AND THEN** the gateway does not pretend that a new prompt can safely execute merely because no TUI parser is involved
