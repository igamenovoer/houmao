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
- the unread-mail polling interval in seconds,
- the effective notification mode,
- the effective appendix text as a string, defaulting to the empty string.

If the managed session is not mailbox-enabled, notifier enablement SHALL fail explicitly rather than silently enabling a broken poll loop.

The gateway SHALL determine notifier support from two inputs:

- the durable mailbox capability published in the runtime-owned session manifest referenced by the attach contract's `manifest_path`,
- the current actionable mailbox state derived from that durable mailbox binding.

The gateway SHALL continue using the manifest as the durable mailbox capability source and SHALL NOT introduce a second persisted mailbox-capability flag in gateway-owned attach or notifier state.

For tmux-backed sessions, current mailbox actionability SHALL be evaluated from runtime-owned validation of the manifest-backed mailbox binding rather than from mailbox-specific `AGENTSYS_MAILBOX_*` projection in the owning tmux session environment.

For joined tmux-backed sessions, notifier support SHALL NOT treat unavailable relaunch posture as an additional readiness precondition once durable mailbox capability and actionable mailbox validation are both satisfied.

If that manifest pointer is missing, unreadable, unparsable, or its launch plan has no mailbox binding, enabling notifier behavior SHALL fail explicitly and SHALL leave notifier inactive.

If the manifest exposes durable mailbox capability but the resulting mailbox binding cannot be validated as actionable for notifier work, notifier enablement SHALL fail explicitly and SHALL leave notifier inactive.

When a caller omits `appendix_text` from `PUT /v1/mail-notifier`, the gateway SHALL preserve the currently stored appendix text unchanged.

When a caller provides non-empty `appendix_text`, the gateway SHALL replace the stored appendix text with that exact string.

When a caller provides `appendix_text=""`, the gateway SHALL clear the stored appendix text.

`DELETE /v1/mail-notifier` SHALL disable polling without erasing the stored appendix text.

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

#### Scenario: Omitted appendix preserves stored notifier appendix
- **WHEN** a caller has previously stored non-empty `appendix_text`
- **AND WHEN** the caller sends `PUT /v1/mail-notifier` without an `appendix_text` field
- **THEN** the gateway preserves the previously stored appendix text unchanged
- **AND THEN** subsequent `GET /v1/mail-notifier` responses return that preserved appendix text

#### Scenario: Provided appendix replaces stored notifier appendix
- **WHEN** a caller sends `PUT /v1/mail-notifier` with non-empty `appendix_text`
- **THEN** the gateway stores that exact appendix text in notifier state
- **AND THEN** subsequent `GET /v1/mail-notifier` responses return the updated appendix text

#### Scenario: Empty appendix clears stored notifier appendix
- **WHEN** a caller sends `PUT /v1/mail-notifier` with `appendix_text=""`
- **THEN** the gateway clears the stored appendix text
- **AND THEN** subsequent `GET /v1/mail-notifier` responses return `appendix_text=""`

#### Scenario: Disable preserves notifier appendix state
- **WHEN** a caller stores non-empty `appendix_text` and later sends `DELETE /v1/mail-notifier`
- **THEN** the gateway disables notifier polling
- **AND THEN** later `GET /v1/mail-notifier` responses still return the previously stored appendix text

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

### Requirement: Gateway mail notifier polls open inbox work
The gateway mail notifier SHALL inspect open inbox work through the gateway-owned shared mailbox facade for the managed session rather than using unread-only `check` behavior.

For this change, open inbox work SHALL mean messages in the current principal's inbox that are not archived or otherwise closed. Messages MAY be read or answered and still remain open inbox work.

When open inbox work is present, the notifier SHALL preserve the existing readiness and queue-admission gates before enqueueing a reminder prompt.

The notifier SHALL record audit inputs in open-work terms, including open-work count and an open-work set identity or equivalent summary, rather than unread-count-only terms.

#### Scenario: Answered inbox mail remains notifier-eligible
- **WHEN** a notifier poll finds an inbox message that is `read=true`, `answered=true`, and `archived=false`
- **AND WHEN** the managed session is eligible for a notifier prompt
- **THEN** the notifier treats that message as open inbox work
- **AND THEN** it may enqueue a reminder prompt through the gateway's durable internal request path

#### Scenario: Archived mail is not notifier-eligible
- **WHEN** a notifier poll finds a message only in the archive box
- **THEN** the notifier does not treat that message as open inbox work
- **AND THEN** it does not enqueue a prompt solely because that archived message exists

### Requirement: Gateway notifier wake-up prompts instruct archive-after-processing workflow
When the gateway mail notifier enqueues an internal reminder for open inbox work, the prompt SHALL concisely announce that the current session has mail in its inbox.

The prompt SHALL direct the agent to use the installed runtime-owned `houmao-process-emails-via-gateway` skill for the current round, list mailbox work through the shared gateway mailbox API, process selected relevant mail, archive only successfully processed mail, and stop after the round.

The prompt SHALL distinguish safe triage from mutating reads by listing a concise current gateway mailbox lifecycle endpoint summary for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`.

The prompt SHALL NOT tell the agent that `mark-read` is the completion action.

#### Scenario: Prompt names archive as completion
- **WHEN** the notifier enqueues a wake-up prompt for open inbox work
- **THEN** the prompt tells the agent to archive successfully processed mail
- **AND THEN** it does not tell the agent to mark messages read as the completion signal

#### Scenario: Prompt advertises peek and read separately
- **WHEN** the notifier prompt provides the current mailbox gateway operation contract
- **THEN** it lists separate routes or action names for peeking and reading mail
- **AND THEN** it communicates that peeking does not mark mail read

### Requirement: Gateway mail notifier supports notification modes
The gateway mail notifier SHALL support a durable notification mode with values `any_inbox` and `unread_only`.

When callers enable or reconfigure the notifier without specifying a mode, the gateway SHALL use `any_inbox`.

The notifier status payload SHALL report the effective mode for both enabled and disabled notifier states.

The notifier poll SHALL always select from the current principal's inbox and SHALL exclude archived or otherwise closed mail. The mode SHALL determine only the read-state filter:

- `any_inbox` SHALL poll with `read_state=any` so read or answered unarchived inbox mail remains notifier-eligible.
- `unread_only` SHALL poll with `read_state=unread` so only unread unarchived inbox mail is notifier-eligible.

The notifier SHALL preserve the existing gateway readiness, prompt-readiness, busy-skip, and internal request-queue admission gates in both modes.

#### Scenario: Omitted mode enables any-inbox notification
- **WHEN** a caller sends `PUT /v1/mail-notifier` with `enabled=true` and `interval_seconds=60` but no `mode`
- **THEN** the gateway stores the notifier as enabled with mode `any_inbox`
- **AND THEN** subsequent `GET /v1/mail-notifier` responses report `mode=any_inbox`

#### Scenario: Any-inbox mode notifies for read answered inbox mail
- **WHEN** the notifier mode is `any_inbox`
- **AND WHEN** a notifier poll finds an inbox message with `read=true`, `answered=true`, and `archived=false`
- **AND WHEN** the gateway is eligible to enqueue a notifier prompt
- **THEN** the notifier treats that message as notification-eligible
- **AND THEN** it may enqueue one internal mail notification request through the gateway queue

#### Scenario: Unread-only mode ignores read inbox mail
- **WHEN** the notifier mode is `unread_only`
- **AND WHEN** a notifier poll finds an inbox message with `read=true` and `archived=false`
- **THEN** the notifier does not treat that message as notification-eligible solely because it remains in the inbox
- **AND THEN** it does not enqueue a prompt solely because of that read message

#### Scenario: Unread-only mode notifies for unread inbox mail
- **WHEN** the notifier mode is `unread_only`
- **AND WHEN** a notifier poll finds an inbox message with `read=false` and `archived=false`
- **AND WHEN** the gateway is eligible to enqueue a notifier prompt
- **THEN** the notifier treats that message as notification-eligible
- **AND THEN** it may enqueue one internal mail notification request through the gateway queue

#### Scenario: Archived mail is not notifier-eligible in either mode
- **WHEN** the notifier mode is `any_inbox` or `unread_only`
- **AND WHEN** a notifier poll finds a message only in the archive box
- **THEN** the notifier does not treat that message as notification-eligible
- **AND THEN** it does not enqueue a prompt solely because that archived message exists

### Requirement: Gateway notifier prompt is mode-aware and preserves archive completion
When the gateway mail notifier enqueues an internal prompt, the prompt SHALL describe the effective notification mode in mailbox workflow terms.

For mode `any_inbox`, the prompt SHALL announce that open inbox mail exists and direct the agent to list open inbox mail for the current round.

For mode `unread_only`, the prompt SHALL announce that unread inbox mail triggered the notification and direct the agent to start from unread inbox mail for the current round.

In both modes, the prompt SHALL direct the agent to archive successfully processed mail and SHALL NOT present reading or marking read as the completion action.

#### Scenario: Any-inbox prompt names open inbox work
- **WHEN** the notifier enqueues a prompt in mode `any_inbox`
- **THEN** the prompt tells the agent that open inbox mail exists
- **AND THEN** it tells the agent to archive successfully processed mail

#### Scenario: Unread-only prompt names unread inbox trigger
- **WHEN** the notifier enqueues a prompt in mode `unread_only`
- **THEN** the prompt tells the agent that unread inbox mail triggered the notification
- **AND THEN** it still tells the agent to archive successfully processed mail

#### Scenario: Prompt does not restore mark-read completion
- **WHEN** the notifier enqueues a prompt in either mode
- **THEN** the prompt does not tell the agent that reading or marking read completes the work
- **AND THEN** the prompt keeps archive as the completion action for successfully processed mail

### Requirement: Mail notifier continues current context for recoverable degraded sessions
For prompt-ready sessions, recoverable degraded chat context SHALL NOT by itself cause an ordinary notifier busy skip and SHALL NOT by itself require clean-context notifier work.

When open inbox work is eligible and all existing readiness, notifier-mode, and queue-admission gates pass, the notifier SHALL enqueue or deliver the normal notifier prompt through current-context prompt work even if recoverable degraded context is present.

Generic current-error diagnostics that do not carry recoverable degraded chat-context evidence SHALL also remain ordinary prompt-ready diagnostics rather than a reason to reset context or busy-skip when the prompt-ready and queue-admission gates pass.

The notifier SHALL preserve explicit clean-context behavior only when a future caller-configured notifier policy or prompt-control request explicitly asks for clean context. It SHALL NOT infer that policy solely from recoverable degraded context.

Notifier audit records MAY include degraded-context detail for diagnostics, but SHALL NOT report clean-context outcomes unless a clean-context workflow actually ran.

#### Scenario: Prompt-ready degraded session gets notifier prompt
- **GIVEN** a gateway mail notifier has open inbox work for the managed session
- **AND GIVEN** the managed session is prompt-ready and its chat context is recoverably degraded
- **AND GIVEN** the notifier's existing queue-admission gates pass
- **WHEN** the notifier poll runs
- **THEN** the notifier enqueues or delivers the normal notifier prompt through current-context prompt work
- **AND THEN** the notifier does not record an ordinary busy skip solely because degraded context is present

#### Scenario: TUI notifier does not reset for degraded context alone
- **GIVEN** a TUI-backed gateway target is prompt-ready with recoverable degraded chat context
- **AND GIVEN** the notifier has eligible open inbox work
- **WHEN** the notifier poll creates notifier work
- **THEN** the notifier does not first send `/new`, `/clear`, or another context-reset signal solely because degraded context is present
- **AND THEN** the notifier audit outcome does not claim clean-context enqueue unless an explicit clean-context workflow ran

#### Scenario: Headless notifier does not force new chat for degraded context alone
- **GIVEN** a native headless gateway target has recoverable degraded chat context
- **AND GIVEN** the notifier has eligible open inbox work and all admission gates pass
- **WHEN** the notifier creates prompt work
- **THEN** the prompt work does not include `chat_session.mode = new` solely because degraded context is present

#### Scenario: Prompt-ready generic error surface receives normal notifier work
- **WHEN** a notifier poll finds open inbox work for a TUI-backed session
- **AND WHEN** the gateway-owned TUI state satisfies the prompt-ready contract while also reporting previous-turn generic error evidence
- **AND WHEN** queue admission passes
- **THEN** the notifier enqueues the normal notifier prompt without first resetting context
- **AND THEN** it does not record a busy skip solely because the previous visible turn contains a generic error

### Requirement: Gateway notifier prompt appends configured runtime appendix text
When the gateway mail notifier enqueues an internal prompt, it SHALL append the configured runtime appendix text only when notifier state currently stores a non-empty `appendix_text`.

The appended appendix text SHALL be rendered after the gateway-owned wake-up context and SHALL remain additive prompt context rather than a replacement for notifier mode, gateway base URL, mailbox API summary, or mailbox-processing skill guidance.

When `appendix_text` is the empty string, the notifier SHALL render no appendix block.

#### Scenario: Non-empty appendix appears in notifier prompt
- **WHEN** notifier state stores non-empty `appendix_text`
- **AND WHEN** the gateway enqueues a notifier prompt
- **THEN** the prompt includes that appendix text as an appended runtime guidance block
- **AND THEN** the prompt still includes the gateway-owned notifier context

#### Scenario: Empty appendix does not render an appendix block
- **WHEN** notifier state stores `appendix_text=""`
- **AND WHEN** the gateway enqueues a notifier prompt
- **THEN** the prompt does not include an appendix block
- **AND THEN** the prompt remains otherwise valid notifier output

### Requirement: Gateway mail notifier exposes context recovery policy
Gateway mail notifier configuration SHALL include an explicit context-error policy and an explicit pre-notification context action.

The context-error policy SHALL support:

- `continue_current`, the default, which preserves current-context notifier delivery even when recoverable degraded chat context is present.
- `clear_context`, an opt-in policy that allows the notifier to start the notifier prompt from clean context when the current degraded diagnostic is a recognized compaction error for the owning CLI tool.

The pre-notification context action SHALL support:

- `none`, the default, which performs no context preflight before notifier prompt delivery.
- `compact`, an opt-in action that runs a supported CLI-tool-specific compaction preflight before notifier prompt delivery.

Notifier status responses SHALL report the effective context-error policy and pre-notification context action for enabled and disabled notifier states.

Existing notifier configurations that do not store these fields SHALL behave as `context_error_policy=continue_current` and `pre_notification_context_action=none`.

#### Scenario: Omitted context policies preserve current behavior
- **WHEN** a caller enables the mail notifier without specifying context recovery fields
- **THEN** the gateway stores or reports `context_error_policy=continue_current`
- **AND THEN** it stores or reports `pre_notification_context_action=none`
- **AND THEN** recoverable degraded context remains eligible for ordinary current-context notifier prompt delivery

#### Scenario: Status reports explicit context policies
- **WHEN** a caller enables the mail notifier with `context_error_policy=clear_context` and `pre_notification_context_action=compact`
- **THEN** subsequent notifier status responses report those effective values
- **AND THEN** the response does not require callers to infer policy from appendix text, logs, or audit rows

### Requirement: Pre-notification compaction runs only for supported CLI tools
When `pre_notification_context_action=compact` is configured, the notifier SHALL run a CLI-tool-specific compaction preflight before submitting the semantic mailbox notification prompt.

For Codex TUI-backed gateway targets, the v1 compaction preflight SHALL use Codex's interactive `/compact` command and wait for the tracked surface to return to prompt-ready posture before continuing.

For CLI tools or backend modes that do not define a supported notifier compaction preflight, notifier enablement or the first affected poll SHALL fail explicitly with a support error. The gateway SHALL NOT silently ignore the `compact` policy.

The compaction preflight SHALL be audited separately from mailbox prompt delivery. A failed compaction preflight SHALL NOT mark mail read, answered, moved, or archived.

#### Scenario: Codex TUI notifier compacts before notification
- **GIVEN** a Codex TUI-backed gateway target supports notifier compaction preflight
- **AND GIVEN** the mail notifier is configured with `pre_notification_context_action=compact`
- **AND GIVEN** eligible open inbox work exists
- **WHEN** the notifier poll reaches prompt delivery
- **THEN** the gateway submits Codex `/compact` before the mailbox notification prompt
- **AND THEN** it waits for prompt-ready posture before submitting the mailbox notification prompt
- **AND THEN** notifier audit records that a compaction preflight was attempted

#### Scenario: Unsupported compact policy fails explicitly
- **GIVEN** a gateway target has no supported notifier compaction preflight for its CLI tool and backend mode
- **WHEN** a caller configures or triggers `pre_notification_context_action=compact`
- **THEN** the gateway reports an explicit support error for that policy
- **AND THEN** it does not claim that pre-notification compaction is active or completed

#### Scenario: Failed compaction preflight does not mutate mailbox state
- **GIVEN** the notifier attempts a pre-notification compaction preflight
- **AND GIVEN** that preflight fails or produces a degraded compaction diagnostic
- **WHEN** the gateway records the notifier poll outcome
- **THEN** unread inbox mail remains unread unless mailbox state is changed through an explicit mailbox operation
- **AND THEN** the failed preflight does not move or archive any mailbox message

### Requirement: Mail notifier clears context only for explicit compaction-error policy
Recoverable degraded chat context SHALL NOT by itself cause mail-notifier clean-context recovery.

When `context_error_policy=clear_context` is configured and the current degraded diagnostic is a recognized compaction error for the owning CLI tool, the notifier SHALL use clean-context prompt delivery before submitting the semantic mailbox notification prompt.

When `context_error_policy=continue_current` is configured, the notifier SHALL use ordinary current-context delivery even if a recognized degraded compaction diagnostic is present, provided existing prompt-readiness and queue-admission gates pass.

When no recognized compaction-error diagnostic is present, `context_error_policy=clear_context` SHALL NOT clear context solely because generic current-error or degraded evidence exists.

#### Scenario: Default policy continues after Codex compaction error
- **GIVEN** a Codex TUI-backed gateway target is prompt-ready with a Codex-specific degraded compaction diagnostic
- **AND GIVEN** the notifier uses the default `context_error_policy=continue_current`
- **WHEN** a notifier poll finds eligible open inbox work and queue admission passes
- **THEN** the notifier submits the mailbox notification prompt through ordinary current-context delivery
- **AND THEN** it does not first send `/new`, `/clear`, or another context-reset signal

#### Scenario: Clear-context policy consumes recognized compaction error
- **GIVEN** a gateway target is prompt-ready with a recognized degraded compaction diagnostic for its owning CLI tool
- **AND GIVEN** the notifier is configured with `context_error_policy=clear_context`
- **WHEN** a notifier poll finds eligible open inbox work and queue admission passes
- **THEN** the notifier runs the supported clean-context workflow before submitting the mailbox notification prompt
- **AND THEN** notifier audit records that clean-context recovery was policy-selected

#### Scenario: Clear-context policy does not reset for generic error
- **GIVEN** a gateway target is prompt-ready with generic current-error evidence but no recognized compaction-error degraded diagnostic
- **AND GIVEN** the notifier is configured with `context_error_policy=clear_context`
- **WHEN** a notifier poll finds eligible open inbox work and queue admission passes
- **THEN** the notifier does not clear context solely because that generic error is visible
- **AND THEN** it either continues current-context delivery or records a non-compaction diagnostic according to the remaining readiness gates

### Requirement: Notifier audit records context policy decisions
Gateway notifier audit records SHALL include enough structured evidence to explain context policy behavior for each poll that reaches context preflight or prompt delivery.

The audit evidence SHALL identify:

- the effective context-error policy,
- the effective pre-notification context action,
- whether compaction preflight was attempted,
- whether clean-context recovery was attempted,
- the owning CLI tool for any degraded diagnostic,
- the tool-scoped degraded error type when present,
- the recovery outcome or failure detail.

Audit outcomes SHALL NOT claim clean-context notification success unless a clean-context workflow actually completed and the mailbox notification prompt was accepted afterward.

#### Scenario: Audit records ordinary current-context decision
- **GIVEN** the notifier is configured with default context policies
- **AND GIVEN** eligible open inbox work is delivered through current-context prompt work
- **WHEN** a caller inspects notifier audit history
- **THEN** the audit evidence identifies `context_error_policy=continue_current`
- **AND THEN** it identifies `pre_notification_context_action=none`
- **AND THEN** it does not claim clean-context recovery

#### Scenario: Audit records policy-selected recovery failure
- **GIVEN** the notifier is configured to clear context for recognized compaction errors
- **AND GIVEN** clean-context recovery fails before the mailbox notification prompt is accepted
- **WHEN** the gateway records the notifier poll
- **THEN** notifier audit records the recovery failure detail
- **AND THEN** it does not report the mailbox notification prompt as successfully enqueued after clean-context recovery

