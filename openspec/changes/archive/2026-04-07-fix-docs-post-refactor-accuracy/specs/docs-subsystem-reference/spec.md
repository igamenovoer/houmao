## MODIFIED Requirements

### Requirement: Operator-facing agent reference uses houmao-mgr as primary example surface

The managed-agent API reference SHALL document the API routes for agent session control and headless turn management.

When the managed-agent API reference documents the headless turn `chat_session` parameter, it SHALL list the five accepted gateway-level modes (`auto`, `new`, `current`, `tool_last_or_new`, `exact`) and note that `auto` and `current` are gateway-level selectors resolved by the gateway before dispatch. The docs SHALL clarify that the internal headless turn API accepts only `new`, `tool_last_or_new`, and `exact`.

#### Scenario: Reader copies a prompt example from public-interfaces.md
- **WHEN** a reader copies a prompt example from the agent reference
- **THEN** the example uses `houmao-mgr` verbs as the primary surface

#### Scenario: Session lifecycle diagram uses houmao-mgr verbs
- **WHEN** a reader checks the session lifecycle diagram in the agent reference
- **THEN** the diagram uses `houmao-mgr` verbs

#### Scenario: Reader understands chat-session mode scope
- **WHEN** a reader checks the `chat_session` parameter in the managed-agent API reference
- **THEN** the page lists all five gateway-level modes (`auto`, `new`, `current`, `tool_last_or_new`, `exact`)
- **AND THEN** the page notes that `auto` and `current` are resolved by the gateway before dispatch to the internal headless turn API
- **AND THEN** the page states that the internal headless turn API accepts only `new`, `tool_last_or_new`, and `exact`
