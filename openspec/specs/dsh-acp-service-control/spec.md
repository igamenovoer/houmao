# dsh-acp-service-control Specification

## Purpose

Specify DeepSeek Harness ACP as a persistent managed service with exact session binding, bounded protocol control, and truthful execution evidence.

## Requirements

### Requirement: DSH service opens one qualified stdio ACP session

The DSH service adapter SHALL launch the native ACP profile, initialize its bidirectional connection, negotiate required operations, and create or exactly resume a native session in the recorded workspace. Multiple managed prompts SHALL share that service and session until an explicit lifecycle or conversation action changes them.

#### Scenario: An operator submits two prompts

- **WHEN** a DSH service admits a second prompt after the first settles
- **THEN** the same ACP process and exact session handle both and no per-turn worker is created

#### Scenario: Exact native resume is unavailable

- **WHEN** a relaunch requests continuity but the negotiated build or native session cannot satisfy it
- **THEN** the launch reports a bounded failure without sending input or creating a different conversation

### Requirement: DSH ACP settlement and reverse requests remain correlated

The DSH adapter SHALL correlate prompt responses, updates, and supported permission requests with the active native session and operation. Native cancellation SHALL target only the verified active session and permit continued reads through settlement. Stop reasons, usage sources, and redacted diagnostics SHALL preserve their native meaning.

#### Scenario: Permission precedes a prompt response

- **WHEN** a qualified DSH permission request arrives while a prompt is pending
- **THEN** the owner applies the selected policy while draining session updates and preserves native hard denials

#### Scenario: A cancel races completion

- **WHEN** the owner receives a late cancel for a settled DSH turn while another turn is eligible
- **THEN** it fences the old request and never sends a session-scoped cancellation against newer work

### Requirement: DSH service scopes configuration to native boundaries

The adapter SHALL supply qualified native-home and ACP initialization inputs at their actual read boundaries. A request-scoped option implemented through a session setting SHALL be isolated and restored before subsequent admission, or rejected before mutation. Uncertain restoration SHALL leave further conflicting work unavailable.

#### Scenario: A request overrides the model

- **WHEN** an admitted prompt applies a temporary session setting and later fails or is cancelled
- **THEN** the adapter verifies the prior setting before releasing admission or reports unresolved state

#### Scenario: MCP configuration changes during service lifetime

- **WHEN** an operator edits a declaration that DSH consumes during ACP session binding
- **THEN** refresh reports the active session's verified coverage and any required new session or relaunch without implicitly restarting the service
