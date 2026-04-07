# agent-gateway-mail-notifier Specification

## Purpose
Define the gateway-owned mail notifier control and polling contract for shared mailbox sessions.
## Requirements
### Requirement: Gateway mail notifier can be configured through dedicated HTTP control routes
The system SHALL provide a gateway-owned mail notifier capability for mailbox-enabled sessions through dedicated HTTP routes served by the gateway sidecar.

That notifier surface SHALL include:

- `PUT /v1/mail-notifier` to enable or reconfigure notifier behavior,
- `GET /v1/mail-notifier` to inspect notifier configuration and runtime status,
- `DELETE /v1/mail-notifier` to disable notifier behavior.

Notifier configuration SHALL include at minimum:

- whether notifier is enabled,
- the unread-mail polling interval in seconds.

If the managed session is not mailbox-enabled, notifier enablement SHALL fail explicitly rather than silently enabling a broken poll loop.

The gateway SHALL determine notifier support from two inputs:

- the durable mailbox capability published in the runtime-owned session manifest referenced by the attach contract's `manifest_path`,
- the current actionable mailbox state derived from that durable mailbox binding.

The gateway SHALL continue using the manifest as the durable mailbox capability source and SHALL NOT introduce a second persisted mailbox-capability flag in gateway-owned attach or notifier state.

For tmux-backed sessions, current mailbox actionability SHALL be evaluated from runtime-owned validation of the manifest-backed mailbox binding rather than from mailbox-specific `AGENTSYS_MAILBOX_*` projection in the owning tmux session environment.

For joined tmux-backed sessions, notifier support SHALL NOT treat unavailable relaunch posture as an additional readiness precondition once durable mailbox capability and actionable mailbox validation are both satisfied.

If that manifest pointer is missing, unreadable, unparsable, or its launch plan has no mailbox binding, enabling notifier behavior SHALL fail explicitly and SHALL leave notifier inactive.

If the manifest exposes durable mailbox capability but the resulting mailbox binding cannot be validated as actionable for notifier work, notifier enablement SHALL fail explicitly and SHALL leave notifier inactive.

#### Scenario: Mail notifier is enabled with an explicit interval
- **WHEN** a caller sends `PUT /v1/mail-notifier` with `enabled=true` and `interval_seconds=60`
- **THEN** the gateway stores that notifier configuration durably
- **AND THEN** subsequent notifier status reads report notifier as enabled with the configured interval

#### Scenario: Mail notifier can be disabled explicitly
- **WHEN** a caller sends `DELETE /v1/mail-notifier` for a gateway-managed session whose notifier is enabled
- **THEN** the gateway disables further notifier polling for that session
- **AND THEN** subsequent notifier status reads report notifier as disabled

#### Scenario: Mail notifier enablement fails for a session without mailbox support
- **WHEN** a caller attempts to enable the mail notifier for a gateway-managed session whose launch plan has no mailbox binding
- **THEN** the gateway rejects that notifier enablement explicitly
- **AND THEN** it does not claim that notifier polling is active for that session

#### Scenario: Mail notifier enablement fails when manifest-backed capability discovery is unavailable
- **WHEN** a caller attempts to enable the mail notifier for a gateway-managed session whose attach contract lacks a readable runtime-owned session manifest
- **THEN** the gateway rejects that notifier enablement explicitly
- **AND THEN** it does not treat any gateway-owned attach or notifier artifact as a substitute mailbox-capability source

#### Scenario: Tmux-backed late registration becomes notifier-ready after durable binding validation
- **WHEN** a tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** runtime-owned mailbox validation reports that binding as actionable for notifier work
- **THEN** the gateway treats notifier support as available for that session without requiring provider relaunch or mailbox-specific tmux env refresh
- **AND THEN** notifier enablement may proceed using that durable-plus-validated mailbox contract

#### Scenario: Joined tmux session without relaunch posture becomes notifier-ready after late registration
- **WHEN** a joined tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** that joined session's relaunch posture is unavailable
- **AND WHEN** runtime-owned mailbox validation reports that binding as actionable for notifier work
- **THEN** the gateway treats notifier support as available for that joined session
- **AND THEN** notifier enablement may proceed without requiring joined-session relaunch posture

#### Scenario: Durable mailbox presence without actionable validation rejects notifier enablement
- **WHEN** a tmux-backed managed session has a durable mailbox binding in its manifest
- **AND WHEN** runtime-owned mailbox validation fails or required transport-local prerequisite material is unavailable for notifier work
- **THEN** the gateway rejects notifier enablement explicitly
- **AND THEN** notifier status reports that the session is not yet actionable for notifier work

### Requirement: Gateway mail notifier polls gateway-owned mailbox state and only schedules notifications when the agent is idle
The gateway mail notifier SHALL inspect unread-mail state through the gateway-owned shared mailbox facade for the managed session rather than by reading filesystem mailbox-local SQLite directly.

For this change, that notifier polling contract SHALL be limited to the mailbox functions supported by both the filesystem transport and the `stalwart` transport, using unread `check` behavior plus normalized message references and metadata.

When unread mail is present, the notifier SHALL enqueue a gateway-owned internal notification request only if:

- request admission is open,
- no gateway request is actively executing,
- queue depth is zero,
- the attached managed prompt surface is currently ready to accept a new prompt through the strongest live readiness signal available for that backend.

For TUI-backed sessions, readiness SHALL require more than tmux-session connectivity. The gateway SHALL require a live prompt-ready posture equivalent to idle-and-ready-for-input state before enqueueing a notifier reminder.

When those conditions are not satisfied, the notifier SHALL skip that interval and retry on a later poll rather than enqueueing a stale reminder behind unrelated work.

The notifier SHALL execute notifications through the gateway's durable internal request path rather than by bypassing the queue with direct terminal injection.

When the notifier enqueues a reminder prompt, that prompt SHALL describe unread mailbox work in transport-neutral shared-mailbox terms and SHALL NOT label the unread set as "filesystem mailbox messages" for a `stalwart` session.

#### Scenario: Idle and prompt-ready gateway schedules one internal mail notification request
- **WHEN** the notifier poll finds unread messages through the gateway-owned shared mailbox facade
- **AND WHEN** gateway request admission is open, active execution is idle, queue depth is zero, and the managed prompt surface is ready for a new prompt
- **THEN** the gateway inserts one internal mail notification request into its durable execution path
- **AND THEN** the reminder reaches the managed agent through the same serialized execution model used for other gateway-managed work

#### Scenario: Filesystem-backed notifier poll uses the shared gateway mailbox facade
- **WHEN** the notifier polls unread mail for a filesystem mailbox-enabled session
- **THEN** the gateway determines unread state through the shared mailbox facade rather than direct mailbox-local SQLite reads
- **AND THEN** the rest of the notifier scheduling rules remain unchanged

#### Scenario: Stalwart-backed notifier poll uses the same shared gateway mailbox facade
- **WHEN** the notifier polls unread mail for a `stalwart` mailbox-enabled session
- **THEN** the gateway determines unread state through the same shared mailbox facade used by the filesystem transport
- **AND THEN** notifier wake-up behavior does not require a transport-specific unread polling path

#### Scenario: Stalwart-backed notifier reminder stays transport-neutral
- **WHEN** the notifier enqueues a reminder for unread mail discovered through a `stalwart` mailbox binding
- **THEN** the reminder prompt describes shared mailbox work without labeling the unread messages as filesystem-specific
- **AND THEN** the reminder still points the managed agent at the runtime-owned mailbox skill flow

#### Scenario: TUI-backed session does not enqueue notifier work until the prompt surface is truly ready
- **WHEN** the notifier poll finds unread messages for a TUI-backed session
- **AND WHEN** the tmux session is still live but the provider UI is not idle and ready for input
- **THEN** the notifier does not enqueue a new reminder for that poll cycle
- **AND THEN** the unread messages remain eligible for a later notifier poll after the TUI returns to prompt-ready posture

#### Scenario: Busy gateway defers mail notification
- **WHEN** the notifier poll finds unread messages but the gateway is already running or queueing work
- **THEN** the notifier does not enqueue a new reminder for that interval
- **AND THEN** the unread messages remain eligible for a later notifier poll when the gateway becomes idle again

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

The later gateway-operations section SHALL emphasize the exact current `gateway.base_url` for that turn.

When the shared gateway mailbox facade is available, that later section SHALL list the full current mailbox endpoint URLs derived from that exact base URL for:

- `GET <gateway.base_url>/v1/mail/status`,
- `POST <gateway.base_url>/v1/mail/check`,
- `POST <gateway.base_url>/v1/mail/send`,
- `POST <gateway.base_url>/v1/mail/reply`,
- `POST <gateway.base_url>/v1/mail/state`.

The prompt MAY reference `houmao-agent-email-comms` as the lower-level operational skill for ordinary mailbox actions in the round, but it SHALL center `houmao-process-emails-via-gateway` as the action-taking workflow for the current round.

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

### Requirement: Gateway notifier prompts use native mailbox-skill invocation and never surface skill-document paths
When a gateway notifier wake-up prompt tells an agent to use installed Houmao mailbox skills, that prompt SHALL use tool-native mailbox-skill invocation guidance or explicit Houmao skill names and SHALL NOT instruct the agent to open `SKILL.md` paths from the copied project or from any visible skill directory.

For notifier prompts that assume Houmao mailbox skills are installed:
- Claude-facing prompts SHALL invoke or reference the installed Houmao mailbox skill through Claude's native skill surface and SHALL NOT point the agent at `skills/.../SKILL.md`.
- Codex-facing prompts SHALL use Codex-native installed-skill triggering for the current round and SHALL NOT point the agent at `skills/.../SKILL.md` or copied project skill paths.
- Gemini-facing prompts SHALL reference the installed Houmao mailbox skill by name and SHALL NOT point the agent at `.agents/skills/.../SKILL.md` for ordinary wake-up rounds.

The prompt MAY still provide the current gateway base URL and the exact `/v1/mail/*` routes for the round, but those routes SHALL complement native installed-skill guidance rather than replace it with a skill-document path workflow.

#### Scenario: Codex notifier prompt uses a native installed-skill trigger
- **WHEN** the gateway renders a wake-up prompt for a mailbox-enabled Codex session with installed Houmao mailbox skills
- **THEN** the prompt uses Codex-native installed-skill invocation guidance for `houmao-process-emails-via-gateway`
- **AND THEN** it does not mention `skills/mailbox/.../SKILL.md` or copied project-local skill paths

#### Scenario: Claude notifier prompt avoids project-local skill-document paths
- **WHEN** the gateway renders a wake-up prompt for a mailbox-enabled Claude session with installed Houmao mailbox skills
- **THEN** the prompt directs Claude to use the installed Houmao mailbox skill through the native Claude skill surface
- **AND THEN** it does not mention `skills/.../SKILL.md` as the operational contract for that round

#### Scenario: Gemini notifier prompt uses skill name rather than installed-path prompting
- **WHEN** the gateway renders a wake-up prompt for a mailbox-enabled Gemini session with installed Houmao mailbox skills
- **THEN** the prompt directs Gemini to use the installed `houmao-process-emails-via-gateway` skill by name
- **AND THEN** it does not require `.agents/skills/.../SKILL.md` path lookup for the ordinary notifier-driven round

### Requirement: Gateway mail notifier keeps notification bookkeeping separate from mailbox read state
The gateway SHALL treat notification bookkeeping and mailbox read state as separate concerns.

The notifier MAY persist gateway-owned metadata such as last poll time or last notification attempt under gateway-owned persistence, but it SHALL NOT redefine mailbox read state from that metadata.

The notifier SHALL NOT require gateway-owned reminder deduplication or reminder-resolution state in order to decide whether unread mail is eligible for another reminder.

Mailbox read or unread truth SHALL come from the selected mailbox transport through the gateway mailbox facade rather than from gateway-owned transport-local persistence.

The gateway SHALL NOT mark a message read merely because:

- unread mail was detected,
- a notifier prompt was accepted into the queue,
- a notifier prompt was delivered successfully to the managed agent.

#### Scenario: Delivered reminder does not auto-mark unread mail as read
- **WHEN** the gateway successfully delivers a mail notification prompt to the managed agent
- **THEN** the underlying unread messages remain unread until mailbox state is updated explicitly through the selected transport
- **AND THEN** notifier bookkeeping does not itself change mailbox read state

#### Scenario: Gateway restart does not turn notifier bookkeeping into unread suppression truth
- **WHEN** the gateway restarts after previously notifying the managed agent about unread mail
- **THEN** the gateway may recover observational notifier metadata such as last poll time or last notification time
- **AND THEN** mailbox read or unread truth still comes from the selected mailbox transport through the gateway mailbox facade rather than from gateway-owned notifier records
- **AND THEN** future reminder eligibility still depends on current unread mail plus live prompt readiness rather than on restored reminder-dedup history

### Requirement: Server-managed notifier control projects the same gateway-owned notifier state
When notifier control is exposed through server-owned managed-agent gateway routes, those server routes SHALL read and write the same gateway-owned notifier configuration and runtime state used by the direct gateway `/v1/mail-notifier` routes.

The server projection SHALL NOT create a second notifier state store, a second unread-state source, or a second deduplication history separate from the gateway-owned notifier records.

The gateway sidecar SHALL remain the source of truth for notifier configuration, polling history, and per-poll audit evidence.

#### Scenario: Enabling notifier through the server route is visible through the direct gateway route
- **WHEN** a caller enables notifier behavior through a server-owned managed-agent gateway route
- **THEN** the corresponding direct gateway `/v1/mail-notifier` read returns the same enabled configuration
- **AND THEN** the system does not maintain separate server-only and gateway-only notifier state

#### Scenario: Disabling notifier through the direct gateway route is visible through the server route
- **WHEN** a caller disables notifier behavior through the direct gateway `/v1/mail-notifier` surface
- **THEN** a later read through the server-owned managed-agent gateway route reports notifier as disabled
- **AND THEN** both surfaces continue reflecting the same gateway-owned notifier truth

