## MODIFIED Requirements

### Requirement: Gateway notifier wake-up prompts summarize unread shared-mailbox work through a template-driven gateway-first contract
When the gateway mail notifier enqueues an internal reminder for unread mail, that reminder SHALL summarize the unread mailbox snapshot in shared-mailbox terms rather than nominating only one actionable target.

That reminder SHALL be rendered from a packaged Markdown template asset rather than assembled entirely from hardcoded Python string literals.

The runtime renderer SHALL fill that template through deterministic string replacement over runtime-generated values and pre-rendered blocks. The implementation SHALL NOT require a general-purpose template engine.

The rendered prompt SHALL direct the agent to discover current mailbox state through `pixi run houmao-mgr agents mail resolve-live` and to obtain the exact live shared-mailbox endpoint from the returned `gateway.base_url`.

When the shared gateway mailbox facade is available, the prompt SHALL direct the agent to use curl against that exact `gateway.base_url` for `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state`.

The prompt SHALL reference both:
- the runtime-owned common gateway mailbox skill path for shared gateway operations, and
- the active transport-specific mailbox skill path for transport-specific context and fallback guidance.

The prompt SHALL explicitly instruct the agent to use the installed runtime-owned common gateway mailbox skill for the current mailbox turn rather than presenting that skill path only as optional supporting material.

Those runtime-owned skill references SHALL use the `houmao-<skillname>` naming convention, including `skills/mailbox/houmao-email-via-agent-gateway/` for the common gateway skill.

When the prompt intends to trigger a Houmao-owned skill, it SHALL include the keyword `houmao` explicitly in the instruction text rather than relying on an implicit or shortened skill name.

For joined sessions adopted through `houmao-mgr agents join`, that installed-skill assumption SHALL apply only when the join workflow performed the default Houmao-owned mailbox skill projection. When join used an explicit opt-out, the notifier prompt SHALL NOT claim that the Houmao-owned mailbox skills are installed.

When multiple unread messages are present, the prompt SHALL include header summaries for every unread message in the current unread snapshot. Each summary entry SHALL include at minimum:
- the opaque `message_ref`,
- optional `thread_ref`,
- sender identity,
- subject,
- `created_at_utc`.

The prompt SHALL instruct the agent to determine which unread message or messages to inspect and handle after checking current mailbox state. It SHALL continue to state that read-state mutation happens only after successful processing of the corresponding message.

Notifier deduplication SHALL remain keyed to the full unread set rather than only to any single message, so unchanged unread mail does not generate repeated reminders solely because the prompt body is richer.

#### Scenario: Template-driven notifier prompt references the manager-owned resolver and gateway skill
- **WHEN** the notifier enqueues a wake-up prompt for unread mail on a mailbox-enabled session with a live shared mailbox facade
- **THEN** the prompt is rendered from a packaged Markdown template
- **AND THEN** it directs the agent to `pixi run houmao-mgr agents mail resolve-live`
- **AND THEN** it tells the agent to use the installed runtime-owned gateway mailbox skill for that mailbox turn
- **AND THEN** it references the runtime-owned gateway mailbox skill path and the current transport-specific mailbox skill path using the `houmao-<skillname>` naming convention

#### Scenario: Notifier prompt includes explicit `houmao` wording when triggering the gateway skill
- **WHEN** the notifier prompt instructs the agent to use the installed gateway mailbox skill
- **THEN** the instruction text names the skill with its `houmao-...` form
- **AND THEN** the prompt includes the keyword `houmao` explicitly instead of relying on an abbreviated or implicit trigger

#### Scenario: Joined-session notifier prompt does not claim installed Houmao skills after join opt-out
- **WHEN** a mailbox-enabled session was adopted through `houmao-mgr agents join` with the explicit opt-out for Houmao mailbox skill installation
- **AND WHEN** the notifier later enqueues a wake-up prompt for that joined session
- **THEN** the prompt does not tell the agent to use Houmao-owned mailbox skills as already-installed assets for that session
- **AND THEN** the prompt still points the agent at the manager-owned live resolver and the supported mailbox operation contract for the session

#### Scenario: Notifier prompt includes all unread message headers in one snapshot
- **WHEN** the notifier finds multiple unread messages through the shared mailbox facade
- **THEN** the enqueued wake-up prompt includes a header summary entry for every unread message in that snapshot
- **AND THEN** each entry includes the opaque message reference plus sender, subject, and creation timestamp context
- **AND THEN** the prompt does not reduce the unread set to only one nominated target

#### Scenario: Prompt teaches curl-first shared mailbox operations through the resolved gateway URL
- **WHEN** the notifier enqueues a wake-up prompt for a session with an attached live gateway
- **THEN** the prompt tells the agent to obtain `gateway.base_url` from `houmao-mgr agents mail resolve-live`
- **AND THEN** it documents curl-based use of `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state` against that exact base URL
- **AND THEN** the agent does not need to guess another localhost port or reconstruct the endpoint from unrelated process state

#### Scenario: Prompt leaves mailbox triage to the agent while preserving explicit read-state discipline
- **WHEN** the notifier enqueues a wake-up prompt for one unread snapshot
- **THEN** the prompt tells the agent to determine which unread message or messages to inspect and handle after checking current mailbox state
- **AND THEN** it still directs the agent to mark messages read only after the corresponding mailbox work succeeds

#### Scenario: Deduplication remains based on the full unread set
- **WHEN** the notifier has already delivered one wake-up prompt for a particular unread snapshot
- **AND WHEN** a later notifier poll sees the same unread set unchanged
- **THEN** the notifier suppresses a duplicate reminder for that unchanged unread snapshot
- **AND THEN** that suppression behavior does not depend on selecting or nominating only one unread target
