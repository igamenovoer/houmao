## MODIFIED Requirements

### Requirement: `houmao-agent-gateway` routes by gateway-specific intent and keeps ordinary messaging on the existing skills
The packaged `houmao-agent-gateway` skill SHALL select commands by gateway-specific intent:

- use `houmao-mgr agents gateway attach|detach|status` or `/houmao/agents/{agent_ref}/gateway...` for gateway lifecycle and summary state,
- use `houmao-mgr agents gateway mail-notifier ...` or `/houmao/agents/{agent_ref}/gateway/mail-notifier` for unread-mail notifier control,
- use direct `{gateway.base_url}/v1/wakeups...` only for wakeup registration, inspection, and cancellation because the current implementation does not project those operations through a higher-level CLI or managed-agent route,
- use direct `{gateway.base_url}/v1/...` only when the task genuinely requires a gateway-only lower-level surface and the exact live base URL is already available from supported discovery.

The packaged `houmao-agent-gateway` skill SHALL delegate ordinary prompt turns, mailbox routing, ordinary mailbox work, or transport-specific mailbox work to:

- `houmao-agent-messaging`
- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The skill SHALL prefer the managed-agent seam first when it already satisfies the current task and SHALL treat direct gateway listener URLs as the lower-level gateway-only path.

#### Scenario: Lifecycle and notifier work stay on the managed-agent seam when possible
- **WHEN** the user asks for gateway attach, detach, status, or mail-notifier control
- **THEN** the skill directs the caller to `houmao-mgr agents gateway ...` or the managed-agent `/houmao/agents/{agent_ref}/gateway...` routes
- **AND THEN** it does not require direct gateway listener discovery when the higher-level seam already satisfies the task

#### Scenario: Wakeups use the direct live gateway route family
- **WHEN** the user asks to create, inspect, or cancel one gateway wakeup job
- **THEN** the skill directs the caller to the live `{gateway.base_url}/v1/wakeups...` route family
- **AND THEN** it does not misdescribe wakeups as a current `houmao-mgr agents gateway ...` subcommand or as a managed-agent API projection that does not exist yet

#### Scenario: Ordinary prompt or mailbox work delegates away from the gateway skill
- **WHEN** the task is one normal prompt turn, one transport-neutral interrupt, or mailbox work rather than gateway lifecycle or gateway-only service control
- **THEN** the skill directs the caller to `houmao-agent-messaging` and the current mailbox skills instead of taking that work itself
- **AND THEN** it does not present the gateway skill as the primary ordinary communication surface
