## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-gateway` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-gateway` under the maintained system-skill asset root.

That skill SHALL instruct agents and operators to handle gateway-specific work through these supported surfaces:

- `houmao-mgr agents gateway attach`
- `houmao-mgr agents gateway detach`
- `houmao-mgr agents gateway status`
- `houmao-mgr agents gateway prompt|interrupt`
- `houmao-mgr agents gateway send-keys`
- `houmao-mgr agents gateway tui state|history|watch|note-prompt`
- `houmao-mgr agents gateway reminders list|get|create|set|remove`
- `houmao-mgr agents gateway mail-notifier status|enable|disable`
- managed-agent HTTP routes under `/houmao/agents/{agent_ref}/gateway...`, including gateway reminder routes when the task is operating through pair-managed authority
- direct live gateway HTTP only when the exact live `{gateway.base_url}` is already available and the task genuinely needs a gateway-only lower-level surface such as `/v1/status`, `/v1/reminders`, or `/v1/mail-notifier`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `lifecycle`
- `discover`
- `gateway-services`
- `reminders`
- `mail-notifier`

That packaged skill SHALL remain the canonical Houmao-owned skill for gateway-specific lifecycle, discovery, gateway-only control, and reminder work whether the caller is another agent with an installed Houmao skill home or an external operator standing outside the managed session.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `agents launch|join|stop|relaunch|cleanup`
- `project easy specialist create|list|get|remove`
- ordinary prompt or mailbox work that is already satisfied by `houmao-agent-messaging` and the mailbox skills
- mailbox transport-specific filesystem or Stalwart internals
- inventing new `houmao-mgr`, managed-agent API, or direct gateway routes that the current implementation does not expose

#### Scenario: Installed skill points the caller at the supported gateway surfaces
- **WHEN** an agent or operator opens the installed `houmao-agent-gateway` skill
- **THEN** the skill directs the caller to the supported gateway lifecycle, reminder, notifier, and gateway-only control surfaces
- **AND THEN** it does not redirect the caller to unrelated live-agent lifecycle, ordinary messaging, or transport-local mailbox repair work

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-gateway` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for lifecycle, discovery, gateway-only services, reminders, and notifier guidance
- **AND THEN** the detailed workflow lives in local action-specific documents rather than in one flattened entry page

#### Scenario: Installed skill keeps non-gateway concerns out of scope
- **WHEN** an agent reads the installed `houmao-agent-gateway` skill
- **THEN** the skill marks ordinary prompt/mail flows, transport-specific mailbox internals, and unrelated live-agent lifecycle work as outside the packaged skill scope
- **AND THEN** it does not present `houmao-agent-gateway` as the generic replacement for `houmao-agent-instance`, `houmao-agent-messaging`, or the mailbox skills

### Requirement: `houmao-agent-gateway` routes by gateway-specific intent and keeps ordinary messaging on the existing skills
The packaged `houmao-agent-gateway` skill SHALL select commands by gateway-specific intent:

- use `houmao-mgr agents gateway attach|detach|status` or `/houmao/agents/{agent_ref}/gateway...` for gateway lifecycle and summary state,
- use `houmao-mgr agents gateway mail-notifier ...` or `/houmao/agents/{agent_ref}/gateway/mail-notifier` for unread-mail notifier control,
- use `houmao-mgr agents gateway reminders list|get|create|set|remove` or `/houmao/agents/{agent_ref}/gateway/reminders...` for reminder creation, inspection, update, and cancellation,
- use direct `{gateway.base_url}/v1/reminders...` only when the task genuinely requires the low-level live reminder HTTP contract and the exact live base URL is already available from supported discovery,
- treat reminder delivery through the supported reminder surfaces as supporting both semantic `prompt` reminders and raw `send_keys` reminders,
- use direct `{gateway.base_url}/v1/...` only when the task genuinely requires a gateway-only lower-level surface and the exact live base URL is already available from supported discovery.

The packaged `houmao-agent-gateway` skill SHALL delegate ordinary prompt turns, mailbox routing, ordinary mailbox work, or transport-specific mailbox work to:

- `houmao-agent-messaging`
- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The skill SHALL prefer the managed-agent seam first when it already satisfies the current task and SHALL treat direct gateway listener URLs as the lower-level gateway-only path.

#### Scenario: Reminders use the native gateway reminder surfaces when available
- **WHEN** the user asks to create, inspect, update, or cancel live gateway reminders
- **THEN** the skill directs the caller to `houmao-mgr agents gateway reminders ...` or the matching `/houmao/agents/{agent_ref}/gateway/reminders...` projection when pair-managed authority is in use
- **AND THEN** it does not misdescribe reminders as an HTTP-only workflow when the supported higher-level reminder surfaces already exist

#### Scenario: Direct live reminder HTTP stays the lower-level contract
- **WHEN** the user asks to debug or inspect the exact live reminder HTTP contract
- **AND WHEN** the exact current `gateway.base_url` is already available from supported discovery
- **THEN** the skill may direct the caller to the live `{gateway.base_url}/v1/reminders...` route family
- **AND THEN** it keeps that direct route family positioned as the lower-level contract rather than the first-choice operator surface

#### Scenario: Ordinary prompt or mailbox work delegates away from the gateway skill
- **WHEN** the task is one normal prompt turn, one transport-neutral interrupt, or mailbox work rather than gateway lifecycle or gateway-only service control
- **THEN** the skill directs the caller to `houmao-agent-messaging` and the current mailbox skills instead of taking that work itself
- **AND THEN** it does not present the gateway skill as the primary ordinary communication surface
