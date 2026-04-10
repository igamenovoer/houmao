## ADDED Requirements

### Requirement: `houmao-server` preserves request-scoped headless execution overrides across managed prompt routes
For headless prompt submission routes, `houmao-server` SHALL accept an optional request-scoped `execution.model` object that uses the same normalized model-selection shape as launch-owned model configuration.

At minimum, this SHALL apply to:

- `POST /houmao/agents/{agent_ref}/turns`
- `POST /houmao/agents/{agent_ref}/requests` when the managed-agent request kind is `submit_prompt`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/gateway/requests` when the gateway request kind is `submit_prompt`

When an eligible attached live gateway handles prompt admission or delivery, `houmao-server` SHALL preserve the same request-scoped `execution.model` payload through the corresponding managed gateway prompt surface.

When direct fallback executes the headless prompt without an attached eligible live gateway, `houmao-server` SHALL preserve the same effective execution semantics through the direct fallback path.

The server SHALL NOT persist the request-scoped execution override into durable managed-agent state or durable turn metadata as later default model state.

For prompt routes that resolve to a TUI-backed managed agent, any supplied execution override SHALL be rejected with validation semantics rather than ignored.

#### Scenario: Gateway-backed managed headless turn preserves execution override
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a managed headless agent with an eligible attached live gateway
- **AND WHEN** the request includes `execution.model.name = "gpt-5.4-mini"`
- **THEN** `houmao-server` returns the normal durable headless `turn_id`
- **AND THEN** the same request-scoped execution override is preserved through gateway-backed live admission for that accepted turn

#### Scenario: Direct-fallback managed headless turn applies the same override semantics
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/turns` for a managed headless agent without an eligible attached live gateway
- **AND WHEN** the request includes `execution.model.reasoning.level = 3`
- **THEN** `houmao-server` accepts the turn through the direct fallback path
- **AND THEN** that accepted turn uses reasoning level `3` without requiring gateway attachment

#### Scenario: Transport-neutral managed-agent prompt accepts execution override for headless target
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/requests` with request kind `submit_prompt`
- **AND WHEN** the resolved managed agent is headless
- **AND WHEN** the request includes `execution.model.name = "gpt-5.4-mini"`
- **THEN** `houmao-server` accepts that managed-agent prompt through the normal transport-neutral route
- **AND THEN** the accepted response still preserves normal headless turn linkage for that request

#### Scenario: Transport-neutral managed-agent prompt rejects execution override for TUI target
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/requests` with request kind `submit_prompt`
- **AND WHEN** the resolved managed agent is TUI-backed
- **AND WHEN** the request includes `execution.model.reasoning.level = 2`
- **THEN** `houmao-server` rejects that request with validation semantics
- **AND THEN** it does not silently drop the execution override and queue or dispatch the TUI prompt anyway

#### Scenario: Managed gateway direct prompt control preserves execution override for headless target
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/gateway/control/prompt` for a managed headless agent
- **AND WHEN** the request includes `execution.model.name = "gpt-5.4-mini"` and `chat_session.mode = current`
- **THEN** `houmao-server` preserves both the explicit chat-session selector and the execution override through the managed gateway prompt-control path
- **AND THEN** the caller does not need to address the gateway listener directly to use that headless execution override
