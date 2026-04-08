## MODIFIED Requirements

### Requirement: `houmao-agent-gateway` routes by gateway-specific intent and keeps ordinary messaging on the existing skills
The packaged `houmao-agent-gateway` skill SHALL select commands by gateway-specific intent:

- use `houmao-mgr agents gateway attach|detach|status` or `/houmao/agents/{agent_ref}/gateway...` for gateway lifecycle and summary state,
- use `houmao-mgr agents gateway mail-notifier ...` or `/houmao/agents/{agent_ref}/gateway/mail-notifier` for unread-mail notifier control,
- use direct `{gateway.base_url}/v1/reminders...` only for reminder creation, inspection, update, and cancellation because the current implementation does not project those operations through a higher-level CLI or managed-agent route,
- treat reminder delivery through direct live gateway routes as supporting both semantic `prompt` reminders and raw `send_keys` reminders,
- use direct `{gateway.base_url}/v1/...` only when the task genuinely requires a gateway-only lower-level surface and the exact live base URL is already available from supported discovery.

The packaged `houmao-agent-gateway` skill SHALL delegate ordinary prompt turns, mailbox routing, ordinary mailbox work, or transport-specific mailbox work to:

- `houmao-agent-messaging`
- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The skill SHALL prefer the managed-agent seam first when it already satisfies the current task and SHALL treat direct gateway listener URLs as the lower-level gateway-only path.

#### Scenario: Reminders use the direct live gateway route family
- **WHEN** the user asks to create, inspect, update, or cancel live gateway reminders
- **THEN** the skill directs the caller to the live `{gateway.base_url}/v1/reminders...` route family
- **AND THEN** it does not misdescribe reminders as a current `houmao-mgr agents gateway ...` subcommand or as a managed-agent API projection that does not exist yet

#### Scenario: Send-keys reminders stay on the reminder HTTP surface
- **WHEN** the user asks for a reminder that should send exact raw keys such as `<[Escape]>` or a slash-command submission
- **THEN** the skill describes that as a `send_keys` reminder on the direct live `/v1/reminders` surface
- **AND THEN** it does not invent a separate reminder CLI family for that workflow

#### Scenario: Ordinary prompt or mailbox work delegates away from the gateway skill
- **WHEN** the task is one normal prompt turn, one transport-neutral interrupt, or mailbox work rather than gateway lifecycle or gateway-only service control
- **THEN** the skill directs the caller to `houmao-agent-messaging` and the current mailbox skills instead of taking that work itself
- **AND THEN** it does not present the gateway skill as the primary ordinary communication surface

### Requirement: `houmao-agent-gateway` describes reminders and mail-notifier honestly
The packaged `houmao-agent-gateway` skill SHALL describe `/v1/reminders` as the supported gateway-owned live reminder surface for one attached gateway.

The skill SHALL state that reminder records are live-gateway in-memory state, are lost on gateway shutdown or restart, and are not a durable unfinished-job queue.

The skill SHALL state that the reminder with the smallest ranking value is the effective reminder and that a paused effective reminder still blocks lower-ranked reminders.

The skill SHALL explain that reminders support two delivery forms:

- semantic `prompt`
- raw `send_keys`

For `send_keys` reminders, the skill SHALL explain:

- `send_keys.sequence` uses exact raw control-input `<[key-name]>` semantics,
- `title` remains reminder metadata and is not terminal input,
- `ensure_enter` defaults to `true`,
- `ensure_enter=false` is the correct choice for pure special-key reminders such as `<[Escape]>`,
- unsupported gateway backends reject `send_keys` reminders explicitly rather than silently downgrading them to prompt text.

The skill SHALL describe `mail-notifier` as unread-mail reminder control for mailbox-enabled sessions and SHALL NOT present it as a general-purpose reminder service for arbitrary unfinished work.

The skill SHALL NOT describe reminders or mail-notifier as durable queued work that survives gateway restart.

#### Scenario: Reminder guidance states the in-memory lifetime and ranking boundary clearly
- **WHEN** an attached agent or operator reads the reminder guidance in the packaged gateway skill
- **THEN** the skill states that reminders are process-local live-gateway state and that the smallest ranking is effective
- **AND THEN** it does not claim that reminder state survives gateway stop or restart

#### Scenario: Send-keys reminder guidance explains ensure-enter default and opt-out
- **WHEN** an attached agent or operator reads the send-keys reminder guidance in the packaged gateway skill
- **THEN** the skill explains that `ensure_enter` defaults to `true`
- **AND THEN** it also explains that pure special-key reminders should set `ensure_enter=false`

#### Scenario: Mail-notifier guidance stays mail-specific
- **WHEN** a caller reads the notifier guidance in the packaged gateway skill
- **THEN** the skill presents `mail-notifier` as unread-mail reminder control through the gateway mailbox facade
- **AND THEN** it does not describe notifier control as the generic answer for arbitrary unfinished-job persistence
