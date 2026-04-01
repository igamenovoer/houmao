## MODIFIED Requirements

### Requirement: Gateway notifier wake-up prompts summarize unread shared-mailbox work through a template-driven gateway-first contract
When the gateway mail notifier enqueues an internal reminder for unread mail, that reminder SHALL summarize the unread mailbox snapshot in shared-mailbox terms rather than nominating only one actionable target.

That reminder SHALL be rendered from a packaged Markdown template asset rather than assembled entirely from hardcoded Python string literals.

The runtime renderer SHALL fill that template through deterministic string replacement over runtime-generated values and pre-rendered blocks. The implementation SHALL NOT require a general-purpose template engine.

The rendered prompt SHALL present two ordered sections:

1. an unread-email summary section for the current unread snapshot, and
2. a gateway-operations section for the current live shared mailbox facade.

The first section SHALL appear before the gateway-operations section.

The first section SHALL explicitly instruct the agent to use the installed runtime-owned `houmao-process-emails-via-gateway` skill to process the notified emails for the current round.

When the prompt intends to trigger that Houmao-owned skill, the instruction text SHALL include the keyword `houmao` explicitly rather than relying on an implicit or shortened skill name.

For joined sessions adopted through `houmao-mgr agents join`, that installed-skill assumption SHALL apply only when the join workflow performed the default Houmao-owned mailbox skill projection. When join used an explicit opt-out, the notifier prompt SHALL NOT claim that the Houmao-owned mailbox skills are installed.

When multiple unread messages are present, the first section SHALL include summary entries for every unread message in the current unread snapshot.

Each summary entry SHALL include at minimum:
- the opaque `message_ref`,
- optional `thread_ref`,
- sender identity,
- subject,
- `created_at_utc`.

Each summary entry MAY include additional non-body metadata already available from the current unread snapshot, but the first section SHALL NOT include `body_preview`, `body_text`, or copied message body content.

The prompt SHALL describe those entries as unread email summaries for the current round rather than as the full work plan.

The rendered prompt SHALL direct the agent to discover current mailbox state through `pixi run houmao-mgr agents mail resolve-live` and to obtain the exact live shared-mailbox endpoint from the returned `gateway.base_url`.

The later gateway-operations section SHALL emphasize the exact current `gateway.base_url` for that turn.

When the shared gateway mailbox facade is available, that later section SHALL list the full current mailbox endpoint URLs derived from that exact base URL for:
- `POST <gateway.base_url>/v1/mail/check`,
- `POST <gateway.base_url>/v1/mail/send`,
- `POST <gateway.base_url>/v1/mail/reply`,
- `POST <gateway.base_url>/v1/mail/state`.

The prompt MAY reference the lower-level `houmao-email-via-agent-gateway` skill or the active transport-specific mailbox skill as supporting material, but it SHALL center `houmao-process-emails-via-gateway` as the action-taking workflow for the current round.

The prompt SHALL instruct the agent to determine which unread message or messages to inspect and handle in the current round, to mark messages read only after successful processing of those same messages, and to stop after the round rather than proactively polling for more mail.

Repeated reminders for unchanged unread mail SHALL continue to summarize the current unread snapshot rather than switching to notifier-owned per-message or per-reminder state.

#### Scenario: Template-driven notifier prompt references the manager-owned resolver and processing skill
- **WHEN** the notifier enqueues a wake-up prompt for unread mail on a mailbox-enabled session with a live shared mailbox facade
- **THEN** the prompt is rendered from a packaged Markdown template
- **AND THEN** it directs the agent to `pixi run houmao-mgr agents mail resolve-live`
- **AND THEN** it tells the agent to use the installed runtime-owned `houmao-process-emails-via-gateway` skill for that notification round

#### Scenario: Joined-session notifier prompt does not claim installed Houmao skills after join opt-out
- **WHEN** a mailbox-enabled session was adopted through `houmao-mgr agents join` with the explicit opt-out for Houmao mailbox skill installation
- **AND WHEN** the notifier later enqueues a wake-up prompt for that joined session
- **THEN** the prompt does not tell the agent to use Houmao-owned mailbox skills as already-installed assets for that session
- **AND THEN** the prompt still points the agent at the manager-owned live resolver and the supported mailbox operation contract for the session

#### Scenario: Notifier prompt includes all unread email summaries without body content
- **WHEN** the notifier finds multiple unread messages through the shared mailbox facade
- **THEN** the first section of the enqueued wake-up prompt includes one summary entry for every unread message in that snapshot
- **AND THEN** each entry includes the opaque message reference plus sender, subject, and creation timestamp context
- **AND THEN** the first section does not include message body content

#### Scenario: Prompt lists full current gateway endpoint URLs
- **WHEN** the notifier enqueues a wake-up prompt for a session with an attached live gateway
- **THEN** the prompt tells the agent to obtain `gateway.base_url` from `houmao-mgr agents mail resolve-live`
- **AND THEN** the later operations section lists the full current mailbox endpoint URLs for `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state`
- **AND THEN** the agent does not need to guess another localhost port or reconstruct the endpoint from unrelated process state

#### Scenario: Prompt bounds the agent to one processing round
- **WHEN** the notifier enqueues a wake-up prompt for one unread snapshot
- **THEN** the prompt tells the agent to choose which unread message or messages to process in the current round
- **AND THEN** it directs the agent to mark messages read only after the corresponding work succeeds
- **AND THEN** it tells the agent to stop after that round and wait for the next notification instead of proactively polling for more mail

#### Scenario: Repeated reminder preserves full unread-snapshot context
- **WHEN** unread mail remains unchanged across multiple prompt-ready notifier cycles
- **THEN** each reminder continues to summarize the current unread snapshot
- **AND THEN** the notifier does not replace that snapshot view with notifier-owned target nomination or reminder-history state
