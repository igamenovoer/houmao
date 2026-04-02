## MODIFIED Requirements

### Requirement: Gateway notifier wake-up prompts summarize unread shared-mailbox work through a template-driven gateway-first contract
When the gateway mail notifier enqueues an internal reminder for unread mail, that reminder SHALL announce that unread shared-mailbox work exists for the current session rather than embedding notifier-rendered unread email summary entries.

That reminder SHALL be rendered from a packaged Markdown template asset rather than assembled entirely from hardcoded Python string literals.

The runtime renderer SHALL fill that template through deterministic string replacement over runtime-generated values and pre-rendered blocks. The implementation SHALL NOT require a general-purpose template engine.

The rendered prompt SHALL present two ordered sections:

1. a wake-up and workflow section for the current mailbox-processing round, and
2. a gateway-operations section for the current live shared mailbox facade.

The first section SHALL appear before the gateway-operations section.

The first section SHALL explicitly instruct the agent to use the installed runtime-owned `houmao-process-emails-via-gateway` skill to process unread mailbox work for the current round.

When the prompt intends to trigger a Houmao-owned skill, it SHALL include the keyword `houmao` explicitly in the instruction text rather than relying on an implicit or shortened skill name.

For joined sessions adopted through `houmao-mgr agents join`, that installed-skill assumption SHALL apply only when the join workflow performed the default Houmao-owned mailbox skill projection. When join used an explicit opt-out, the notifier prompt SHALL NOT claim that the Houmao-owned mailbox skills are installed.

The first section SHALL tell the agent that unread shared-mailbox work exists and that the agent is responsible for listing unread mail through the shared gateway mailbox API for the current round.

The first section SHALL instruct the agent to choose which unread email or emails are relevant to process in the current round, to complete that work, to mark only successfully processed emails read, and to stop after the round rather than proactively polling for more mail.

The notifier prompt SHALL NOT include notifier-rendered unread email summary entries, copied message body content, `body_preview`, or `body_text`.

The prompt SHALL provide the exact current `gateway.base_url` for the current round directly rather than directing the agent to rediscover it through a manager-owned resolver command.

The later gateway-operations section SHALL emphasize that exact current `gateway.base_url` for that turn.

When the shared gateway mailbox facade is available, that later section SHALL list the full current mailbox endpoint URLs derived from that exact base URL for:
- `GET <gateway.base_url>/v1/mail/status`,
- `POST <gateway.base_url>/v1/mail/check`,
- `POST <gateway.base_url>/v1/mail/send`,
- `POST <gateway.base_url>/v1/mail/reply`,
- `POST <gateway.base_url>/v1/mail/state`.

The prompt MAY reference the lower-level `houmao-email-via-agent-gateway` skill or the active transport-specific mailbox skill as supporting material, but it SHALL center `houmao-process-emails-via-gateway` as the action-taking workflow for the current round.

Repeated reminders for unchanged unread mail SHALL continue to announce unread work and provide the current gateway bootstrap contract rather than switching to notifier-owned per-message or per-reminder state.

#### Scenario: Template-driven notifier prompt bootstraps one gateway mailbox round without embedded unread summaries
- **WHEN** the notifier enqueues a wake-up prompt for unread mail on a mailbox-enabled session with a live shared mailbox facade
- **THEN** the prompt is rendered from a packaged Markdown template
- **AND THEN** it tells the agent to use the installed runtime-owned `houmao-process-emails-via-gateway` skill for that notification round
- **AND THEN** it provides the exact live gateway base URL and full mailbox endpoint URLs for the current round
- **AND THEN** it does not embed unread email summary entries in the prompt

#### Scenario: Joined-session notifier prompt does not claim installed Houmao skills after join opt-out
- **WHEN** a mailbox-enabled session was adopted through `houmao-mgr agents join` with the explicit opt-out for Houmao mailbox skill installation
- **AND WHEN** the notifier later enqueues a wake-up prompt for that joined session
- **THEN** the prompt does not tell the agent to use Houmao-owned mailbox skills as already-installed assets for that session
- **AND THEN** the prompt still states that unread mailbox work exists and provides the supported gateway mailbox operation contract for the round

#### Scenario: Prompt tells the agent to list unread mail through the gateway itself
- **WHEN** the notifier enqueues a wake-up prompt for a mailbox-enabled session with unread mail
- **THEN** the prompt tells the agent that unread shared-mailbox work exists
- **AND THEN** it directs the agent to list unread mail through the shared gateway mailbox API for the current round
- **AND THEN** the notifier prompt does not precompute or embed unread message summaries for that round

#### Scenario: Prompt lists full current gateway endpoint URLs including mailbox status
- **WHEN** the notifier enqueues a wake-up prompt for a session with an attached live gateway
- **THEN** the later operations section lists the full current mailbox endpoint URLs for `/v1/mail/status`, `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state`
- **AND THEN** the agent does not need to guess another localhost port or reconstruct the endpoint from unrelated process state

#### Scenario: Prompt bounds the agent to one processing round
- **WHEN** the notifier enqueues a wake-up prompt for unread mailbox work
- **THEN** the prompt tells the agent to choose which unread email or emails to process in the current round
- **AND THEN** it directs the agent to mark messages read only after the corresponding work succeeds
- **AND THEN** it tells the agent to stop after that round and wait for the next notification instead of proactively polling for more mail

#### Scenario: Repeated reminder preserves gateway bootstrap behavior without per-message prompt state
- **WHEN** unread mail remains unchanged across multiple prompt-ready notifier cycles
- **THEN** each reminder continues to announce unread mailbox work and provide the current gateway bootstrap contract
- **AND THEN** the notifier does not replace that behavior with notifier-owned per-message nomination or reminder-history state
