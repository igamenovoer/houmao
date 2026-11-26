# Agent Mailbox System Skills Delta

## MODIFIED Requirements

### Requirement: Gateway email-processing skill covers compact reply receipts and permission failure handling
`houmao-process-emails-via-gateway` SHALL document the compact CLI reply receipt and the `POST /v1/mail/{channel}/reply` action response, with read-only reconciliation on the same binding and explicit fail-closed reporting on `mail.reply` or `mail.attachment.owner_file` authorization failures.

#### Scenario: Agent reconciles reply receipts and permission refusals during a round
- **WHEN** a managed agent replies to or attaches files for a notified email during a gateway round
- **THEN** the workflow uses the CLI `message_ref` or HTTP `message.message_ref` for a same-binding `peek` when needed, and treats offline deposit and provider submission as distinct transport outcomes
- **AND THEN** a `mail.reply` or `mail.attachment.owner_file` denial or an unconfirmed required reply leaves the message open for follow-up

### Requirement: Gateway email-processing skill preserves fail-closed round, reply-hardening, and non-polling invariants
`houmao-process-emails-via-gateway` SHALL preserve agent-only `## Actor Frame Gate`, fail-closed reliance on prompt-supplied `gateway_base_url`, `channel`, and `expected_binding_id`, stalled-work-first ordering, `one_off` lowest-priority (`--after-all` / `start_after_seconds: 15`) reply hardening, and stopping without polling. The binding's placement capability governs filing after successfully processing and replying.

#### Scenario: Missing gateway URL or binding mismatch terminates the round fail-closed
- **WHEN** a notifier prompt lacks `gateway_base_url`, `channel`, or `expected_binding_id`, or the binding mismatches
- **THEN** `houmao-process-emails-via-gateway` stops with a contract failure without running `resolve-live`
- **AND THEN** a successful round archives completed items after any required reply where the binding permits it, or reports them for independently authorized owner filing on a protected binding

### Requirement: Runtime-owned gateway email processing skill defines round-oriented notified email workflow
The system SHALL provide a projected runtime-owned mailbox skill `houmao-process-emails-via-gateway` that defines the workflow for processing gateway-notified Inbox work in bounded rounds.

The `houmao-process-emails-via-gateway/SKILL-MAIN.md` router and `commands/process-round.md` SHALL require the notifier prompt's exact `gateway_base_url`, explicit `offline|online` channel, and `expected_binding_id` for the current round.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The workflow SHALL start by using the shared gateway mailbox API itself to inspect current mailbox state for the round, including listing Inbox mail according to the prompt's notification mode through the shared `/v1/mail/*` surface.

That workflow SHALL start from current mode-eligible metadata such as sender identity, subject, timestamps, and opaque message references before deciding which listed emails are relevant for the current round.

The workflow MAY use additional non-body metadata or lightweight gateway-visible detail to shortlist candidate emails, but it SHALL treat message-body inspection as a later step rather than as part of the initial reminder summary.

Once the workflow selects one or more task-relevant emails for the current round, it SHALL direct the agent to inspect all selected emails needed to decide and complete the work for that round.

Where inspection must leave read state intact until work succeeds, the workflow SHALL use non-mutating `peek`. Deferred or unfinished mail SHALL remain unread in `unread_only` rounds when it started unread.

In an `unread_only` round, the agent SHALL mark successfully processed mail read if it remains unread and the selected binding supports that state change. The workflow SHALL keep read-state changes separate from filing.

The workflow SHALL leave unread emails that were deferred, skipped, or not completed in the unread set for later notifier-driven rounds.

After the agent completes the selected round of work, the workflow SHALL direct the agent to stop and wait for the next notifier wake-up rather than proactively checking for new mail on its own.

The workflow SHALL treat upstream gateway polling, unread snapshot updates, and mailbox-selection rules as outside the agent’s concern for that completed round.

Missing notifier coordinates or a stale binding SHALL end the round with its contract or binding error. The workflow SHALL keep the selected gateway, channel, and binding for all effects during the round.

`commands/process-round.md` SHALL confirm required replies through the compact write receipt and use `peek` on the same channel and binding for any needed read-only reconciliation. On `mail.reply` or `mail.attachment.owner_file` refusal, it SHALL report the exact refusal and leave the message open. A submission-only or uncertain required reply SHALL leave the work open until confirmed.

`references/reply-hardening.md` SHALL preserve optional, lowest-priority `one_off` reminder guidance. It SHALL retain the exact notifier coordinates and reply reference and require a read-only reply-state check before retrying. The round SHALL remove unfired reply reminders after a confirmed ordinary reply and use the binding's authorized completion path for successfully completed messages.

#### Scenario: Metadata-first triage follows an agent-run unread listing step
- **WHEN** the agent begins a notifier-driven email processing round in `unread_only` mode
- **THEN** the workflow directs the agent to inspect current unread mail through the shared gateway mailbox API
- **AND THEN** the workflow starts triage from current unread metadata such as sender, subject, timestamps, and opaque references
- **AND THEN** the agent does not need notifier-rendered unread summaries to start the round

#### Scenario: Selected round-relevant emails are fully inspected before action
- **WHEN** the workflow selects one or more unread emails as relevant to the current round
- **THEN** the workflow directs the agent to inspect all selected emails needed to decide and perform the work for that round
- **AND THEN** the workflow does not require unrelated unread emails to be fully inspected first

#### Scenario: Successfully processed emails are marked read while deferred emails remain unread
- **WHEN** the agent completes work for some but not all unread emails during an `unread_only` round
- **THEN** the workflow directs the agent to mark only successfully processed emails that remain unread when marking is supported
- **AND THEN** deferred or unfinished emails remain unread for later notifier-driven handling

#### Scenario: Completed round waits for the next notification
- **WHEN** the agent finishes the selected work for one email-processing round
- **THEN** the workflow directs the agent to stop rather than proactively polling for more mail
- **AND THEN** the agent waits for the next notifier-triggered wake-up to begin another round

#### Scenario: Missing base URL is treated as a notifier-round contract failure
- **WHEN** the agent begins the notifier-driven workflow for one round
- **AND WHEN** the current round context does not provide the gateway base URL
- **THEN** the workflow does not silently switch to manager-based rediscovery for that round
- **AND THEN** the missing gateway bootstrap is treated as a contract failure for the current wake-up

#### Scenario: A Required Reply Remains Unconfirmed or Is Refused

- **WHEN** a required reply produces a submission-only receipt, remains uncertain, or is refused
- **THEN** the round reports the result and leaves the message open while the reply remains unconfirmed
- **AND THEN** any reply-state check stays on the original channel and binding and any later reply still requires the same authority

### Requirement: Projected mailbox system skills keep routine attached-session actions on the shared gateway facade

When a live gateway exposes the shared `/v1/mail/*` mailbox surface for a mailbox-enabled session, the projected mailbox system skills SHALL use the shared gateway facade for ordinary mailbox work.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Projected mailbox system skills for filesystem and `stalwart` SHALL resolve current mailbox state through `houmao-mgr agents self mail resolve-live` and use a runtime-owned client for live calls. Managed self commands SHALL sign the challenge with the current generation's key. Scoped admins SHALL use an explicit signing key. Skill text, resolver output, and shell examples SHALL omit keys, proof material, and private credential references.

The skills SHALL use the existing separately authorized manager path for ordinary mailbox work when the live gateway is absent. Ordinary mailbox calls through this path SHALL respect the backend's placement restrictions on a protected binding. An admission refusal or unavailable policy from a protected gateway SHALL end the request. Lifecycle actions SHALL retain the selected channel and expected binding. Manager lifecycle commands SHALL include `--channel offline|online`.

Ordinary mailbox work includes:

- checking unread mail
- sending one new message
- replying to one existing message
- marking one processed message read

When projected mailbox skills use `houmao-mgr agents self mail ...` without a live gateway, they SHALL preserve the manager command's authority-aware result:

- `authoritative: true` means Houmao verified the mailbox outcome through manager-owned or gateway-backed execution
- `authoritative: false` means Houmao submitted the request through a TUI-mediated path and separate verification is required

Thin session-local helpers SHALL delegate to the runtime-owned gateway client or maintained `houmao-mgr` mailbox commands. For attached filesystem and `stalwart` sessions, the routine fallback SHALL be manager-owned and transport-neutral.

#### Scenario: Attached mailbox session uses the shared gateway facade when available

- **WHEN** a mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** the skill resolves the current endpoint through `houmao-mgr agents self mail resolve-live`
- **AND THEN** its runtime-owned client signs the request challenge with the current generation's self key

#### Scenario: Mailbox session without gateway falls back to `houmao-mgr agents mail`

- **WHEN** a mailbox-enabled session has no live shared gateway mailbox facade and the caller has existing manager authority
- **THEN** the skill directs the agent to use `houmao-mgr agents self mail ...` for routine mailbox work
- **AND THEN** the manager uses the established transport-neutral path

#### Scenario: Protected gateway refuses mailbox access

- **WHEN** the runtime-owned client receives an authentication or authorization failure for a protected mailbox operation
- **THEN** it surfaces the refusal as the request outcome
- **AND THEN** neither a local transport nor an admin binding is used as fallback

#### Scenario: Non-authoritative manager fallback result triggers explicit verification

- **WHEN** the manager returns `authoritative: false` for routine send or reply
- **THEN** the skill treats the result as submission-only
- **AND THEN** it verifies the result through supported mailbox state before treating delivery as complete

#### Scenario: Thin shell helpers stay wrappers over supported surfaces

- **WHEN** a projected mailbox skill provides a shell helper for local gateway work
- **THEN** that helper delegates to the runtime-owned client or maintained scoped mailbox commands
- **AND THEN** the same target and credential selection governs the operation

### Requirement: Runtime-owned mailbox skill projection pairs a unified ordinary mailbox skill with the separate processing workflow
The agent pack's protected composition SHALL include two distinct mailbox logical routines.

`houmao-process-emails-via-gateway` SHALL own notifier-triggered, bounded Inbox work rounds. Its `process-round` workflow SHALL use prompt-supplied gateway coordinates, perform metadata-first triage, inspect selected messages, finish work and any required replies, follow the binding's authorized completion path, and stop for the next notifier wake-up.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

`houmao-agent-email-comms` SHALL own ordinary discovery, status, list, peek, read, send, post, reply, mark, move, and archive behavior where the selected binding supports each operation. It SHALL prefer a gateway base URL already present in prompt or route context and SHALL use the manager-owned live resolver only when current context lacks that URL. Filesystem and Stalwart guidance SHALL remain internal to this protected routine.

The public agent entrypoint SHALL route to the correct protected routine from operation and notifier context. It SHALL NOT project transport-specific or old compatibility mailbox skills as top-level directories.

#### Scenario: Notified round chooses processing routine
- **WHEN** verified agent context contains a notifier-triggered unread-mail round and gateway URL
- **THEN** the agent entrypoint routes to protected `houmao-process-emails-via-gateway`
- **AND THEN** the round stops after processing the selected work and performing any ordinary archive the binding supports

#### Scenario: Ordinary send chooses email-comms routine
- **WHEN** a verified managed agent asks to send or reply outside a notifier round
- **THEN** the agent entrypoint routes to protected `houmao-agent-email-comms`
- **AND THEN** the routine applies the ordinary mailbox discovery and transport guidance

#### Scenario: Top-level mailbox compatibility paths stay absent
- **WHEN** the agent pack is installed
- **THEN** the tool-native skill root does not contain top-level `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, or transport-specific mailbox compatibility skills

#### Scenario: Claude mailbox-enabled session receives the processing skill and unified ordinary-mailbox skill
- **WHEN** the runtime starts a mailbox-enabled Claude session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/` and `skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** Claude can discover both skills through native skill discovery without relying on a mailbox namespace subtree
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Codex mailbox-enabled session receives the processing skill and unified ordinary-mailbox skill
- **WHEN** the runtime starts a mailbox-enabled Codex session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/` and `skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** the agent can discover both skills through native skill discovery without relying on a mailbox namespace subtree or hidden `.system` entries
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Gemini mailbox-enabled session receives native top-level unified mailbox skills
- **WHEN** the runtime starts a mailbox-enabled Gemini session
- **THEN** it projects `.gemini/skills/houmao-process-emails-via-gateway/` and `.gemini/skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** Gemini can discover both skills through native skill discovery without relying on a `mailbox/` namespace subtree
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Processing skill remains the notifier-round workflow entrypoint
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the runtime-owned `houmao-process-emails-via-gateway` skill is already projected into that session through the tool-native visible mailbox skill surface
- **AND THEN** notifier prompts may instruct the agent to use that installed skill directly for the current mailbox round
- **AND THEN** ordinary mailbox actions within that round may rely on `houmao-agent-email-comms` as supporting material

#### Scenario: Unified ordinary-mailbox skill remains the operational reference
- **WHEN** an agent opens the installed `houmao-agent-email-comms` skill document from the visible mailbox skill surface for its tool
- **THEN** that entry document points the agent at internal action-specific or transport-specific subdocuments for resolver and mailbox-operation behavior
- **AND THEN** it does not replace `houmao-process-emails-via-gateway` as the notifier-facing entrypoint
- **AND THEN** it does not require a separate installed top-level transport skill for filesystem or Stalwart guidance

### Requirement: Runtime-owned mailbox workflow skills use archive as completion
Projected runtime-owned mailbox workflow skills SHALL use archive to close processed Inbox work on bindings that support ordinary archive. On protected bindings, the agent SHALL report successfully processed messages for independently authorized mailbox-owner filing through the backend and finish the round after any required reply succeeds.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The `houmao-process-emails-via-gateway` workflow SHALL direct agents to list open inbox work through the gateway, choose relevant messages for the current round, peek or read selected messages intentionally, perform the requested work, reply or acknowledge when appropriate, archive only successfully processed messages where ordinary archive is supported, and stop after the round.

Deferred, skipped, or not-yet-completed messages SHALL remain unarchived so later notifier rounds can wake the agent again.

#### Scenario: Successfully processed mail is archived
- **WHEN** an agent finishes processing selected mailbox work during a notifier-driven round on a binding that supports ordinary archive
- **THEN** the projected workflow skill instructs the agent to archive the successfully processed messages through the gateway or manager fallback surface
- **AND THEN** unfinished messages remain unarchived for later notification

#### Scenario: A protected mailbox leaves filing to the backend

- **WHEN** an agent finishes selected work and any required reply on a protected binding
- **THEN** the skill directs the agent to report the completed messages for independently authorized owner filing and end the round
- **AND THEN** the skill omits ordinary archive, move, and placement-changing mark from the round and forbids switching to a fallback to perform them

### Requirement: Runtime-owned mailbox skills distinguish list, peek, read, mark, move, and archive
Projected runtime-owned mailbox skills SHALL present the ordinary mailbox action set as status, list, peek, read, send, post, reply, mark, move, archive, and resolve-live where the selected binding supports each action.

The skills SHALL explain that listing and peeking leave read state intact, reading sets read, reply marks the parent answered, and archive closes processed Inbox work where the binding permits it.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skills SHALL keep manual marking available as a repair or operator-directed action rather than as the normal completion step for processed mail. `move`, `archive`, and `mark` with an archived-state update SHALL require explicit binding placement capability even when ordinary read-state updates are supported.

#### Scenario: Skill user can inspect without marking read
- **WHEN** an agent follows projected mailbox skill guidance to inspect a message for triage
- **THEN** the skill presents `peek` as the non-mutating body-inspection action
- **AND THEN** it reserves `read` for the action that marks the message read

#### Scenario: Manual marking is not the normal completion path
- **WHEN** an agent follows projected mailbox skill guidance after completing a mailbox task
- **THEN** the skill directs the agent to archive the processed message where ordinary archive is supported
- **AND THEN** it presents manual `mark` only for explicit state repair or operator-directed state changes

### Requirement: Notifier-driven mailbox skills honor notification mode
The runtime-owned `houmao-process-emails-via-gateway` workflow skill SHALL understand notifier prompts that identify notification mode as `any_inbox` or `unread_only`.

When the prompt identifies mode `any_inbox`, the workflow SHALL direct the agent to list open inbox mail through the shared gateway mailbox API and process relevant selected mail for the round.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When the prompt identifies mode `unread_only`, the workflow SHALL direct the agent to start from unread inbox mail through the shared gateway mailbox API for that round.

In both modes, the workflow SHALL close successfully processed Inbox work through archive where the selected binding supports ordinary archive. Reading, peeking, replying, or acknowledging SHALL leave placement to the backend.

#### Scenario: Any-inbox notification uses open inbox triage
- **WHEN** an agent begins a notifier-driven round whose prompt states mode `any_inbox`
- **THEN** the workflow skill directs the agent to list open inbox mail through the shared gateway mailbox API
- **AND THEN** where ordinary archive is supported, selected processed mail is archived only after the corresponding work and any required reply succeed

#### Scenario: Unread-only notification starts from unread inbox triage
- **WHEN** an agent begins a notifier-driven round whose prompt states mode `unread_only`
- **THEN** the workflow skill directs the agent to start from unread inbox mail through the shared gateway mailbox API
- **AND THEN** ordinary archive closes successfully processed mail where the binding supports it

#### Scenario: Skill does not restore read-as-completion semantics
- **WHEN** an agent follows the notifier-driven workflow in either mode
- **THEN** the workflow treats marking a message read as a change to unread eligibility
- **AND THEN** deferred, skipped, or unfinished messages remain unarchived for later handling according to the configured notifier mode

#### Scenario: The agent ends a round while Inbox mail remains on a protected binding

- **WHEN** the notified work is complete and the backend still lists the processed mail in Inbox
- **THEN** the workflow directs the agent to report the successfully processed mail for independently authorized owner filing and end the round
- **AND THEN** `any_inbox` can remind the agent again while the mail remains in Inbox, while `unread_only` applies the current read state

### Requirement: Static shared routines preserve distinct mailbox owners
The static `houmao-shared-routines` skill SHALL own separate parent-scoped children for ordinary email communication and notifier-driven gateway email rounds.

`houmao-agent-email-comms` SHALL preserve ordinary resolver, status, list, peek, read, send, post, reply, mark, move, archive, and transport fallback behavior where each operation is supported on the selected binding. `houmao-process-emails-via-gateway` SHALL preserve one prompt-bootstrapped, metadata-first, stop-after-round workflow.

#### Scenario: Verified agent receives notifier prompt
- **WHEN** the agent entrypoint receives a notifier-driven round with the exact gateway base URL
- **THEN** it delegates through static shared routines to `houmao-process-emails-via-gateway`
- **AND THEN** the selected child stops after the bounded round

#### Scenario: Verified agent sends ordinary mail
- **WHEN** the agent entrypoint receives an ordinary send or reply request
- **THEN** it delegates through static shared routines to `houmao-agent-email-comms`
- **AND THEN** it does not use the notifier-round child

### Requirement: Mailbox routines triage bounded metadata pages
Ordinary and notifier-driven routines SHALL start with one bounded metadata page on the selected channel and binding. They SHALL page only within the round budget and fetch content only for selected messages. They SHALL use the authorized filing path only for successfully processed mail after any required replies and stop after the round.

#### Scenario: Inbox is larger than one processing round
- **WHEN** the first metadata page has continuation but the round budget is reached
- **THEN** the routine leaves deferred work unarchived for later periodic reminders
- **AND THEN** it does not fetch all retained bodies before selecting work

#### Scenario: Bounded List Examples Pin the Selected Binding

- **WHEN** the routine illustrates a direct HTTP list request
- **THEN** the example uses `schema_version: 3`, `expected_binding_id`, and a bounded metadata-only listing without `include_body`

#### Scenario: Metadata is insufficient for a selected task
- **WHEN** an agent selects a message as relevant
- **THEN** it explicitly peeks or reads the needed content and checks any completeness limitation
- **AND THEN** it does not assume a preview is the full task request
