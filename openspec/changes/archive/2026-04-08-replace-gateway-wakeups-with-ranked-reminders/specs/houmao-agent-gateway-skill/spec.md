## ADDED Requirements

### Requirement: `houmao-agent-gateway` describes reminders and mail-notifier honestly
The packaged `houmao-agent-gateway` skill SHALL describe `/v1/reminders` as the supported gateway-owned live reminder surface for one attached gateway.

The skill SHALL state that reminder records are live-gateway in-memory state, are lost on gateway shutdown or restart, and are not a durable unfinished-job queue.

The skill SHALL state that the reminder with the smallest ranking value is the effective reminder and that a paused effective reminder still blocks lower-ranked reminders.

The skill SHALL describe `mail-notifier` as unread-mail reminder control for mailbox-enabled sessions and SHALL NOT present it as a general-purpose reminder service for arbitrary unfinished work.

The skill SHALL NOT describe reminders or mail-notifier as durable queued work that survives gateway restart.

#### Scenario: Reminder guidance states the in-memory lifetime and ranking boundary clearly
- **WHEN** an attached agent or operator reads the reminder guidance in the packaged gateway skill
- **THEN** the skill states that reminders are process-local live-gateway state and that the smallest ranking is effective
- **AND THEN** it does not claim that reminder state survives gateway stop or restart

#### Scenario: Paused reminder guidance states the blocking behavior clearly
- **WHEN** an attached agent or operator reads the reminder guidance in the packaged gateway skill
- **THEN** the skill explains that a paused effective reminder still blocks lower-ranked reminders
- **AND THEN** it does not imply that pausing automatically promotes the next reminder

#### Scenario: Mail-notifier guidance stays mail-specific
- **WHEN** a caller reads the notifier guidance in the packaged gateway skill
- **THEN** the skill presents `mail-notifier` as unread-mail reminder control through the gateway mailbox facade
- **AND THEN** it does not describe notifier control as the generic answer for arbitrary unfinished-job persistence

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
- `houmao-mgr agents gateway mail-notifier status|enable|disable`
- managed-agent HTTP routes under `/houmao/agents/{agent_ref}/gateway...`
- direct live gateway HTTP only when the exact live `{gateway.base_url}` is already available and the task genuinely needs a gateway-only surface such as `/v1/status`, `/v1/reminders`, or `/v1/mail-notifier`

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
- **THEN** the skill directs the caller to the supported gateway lifecycle, discovery, gateway-only control, and reminder surfaces
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
- use direct `{gateway.base_url}/v1/reminders...` only for reminder creation, inspection, update, and cancellation because the current implementation does not project those operations through a higher-level CLI or managed-agent route,
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

#### Scenario: Reminders use the direct live gateway route family
- **WHEN** the user asks to create, inspect, update, or cancel live gateway reminders
- **THEN** the skill directs the caller to the live `{gateway.base_url}/v1/reminders...` route family
- **AND THEN** it does not misdescribe reminders as a current `houmao-mgr agents gateway ...` subcommand or as a managed-agent API projection that does not exist yet

#### Scenario: Ordinary prompt or mailbox work delegates away from the gateway skill
- **WHEN** the task is one normal prompt turn, one transport-neutral interrupt, or mailbox work rather than gateway lifecycle or gateway-only service control
- **THEN** the skill directs the caller to `houmao-agent-messaging` and the current mailbox skills instead of taking that work itself
- **AND THEN** it does not present the gateway skill as the primary ordinary communication surface

## REMOVED Requirements

### Requirement: `houmao-agent-gateway` describes wakeups and mail-notifier honestly
**Reason**: Wakeups are being replaced by reminders with ranking and pause semantics, so the old wakeup-focused guidance no longer matches the supported gateway contract.
**Migration**: Describe `/v1/reminders` as the supported live reminder surface and keep `mail-notifier` guidance limited to mailbox-specific unread-mail behavior.
