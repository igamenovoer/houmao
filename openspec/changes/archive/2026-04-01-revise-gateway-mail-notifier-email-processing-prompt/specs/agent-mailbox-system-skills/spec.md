## MODIFIED Requirements

### Requirement: Runtime-owned mailbox skill projection separates gateway operations from transport-specific guidance and uses Houmao-owned skill naming
The system SHALL project a round-oriented runtime-owned mailbox workflow skill for gateway-notified email processing into every mailbox-enabled session in addition to the lower-level common gateway mailbox skill and the active transport-specific mailbox skill.

Projected Houmao-owned mailbox skills SHALL use a `houmao-<skillname>` naming convention under the visible mailbox subtree so runtime-owned Houmao skills are distinguishable from role-authored or third-party skill names.

That `houmao-<skillname>` convention SHALL also define the activation boundary for Houmao-owned skills: the instruction text must include the keyword `houmao` when it intends to trigger a Houmao-owned skill.

For current adapters whose active skill destination is `skills`, the round-oriented workflow skill SHALL be available at `skills/mailbox/houmao-process-emails-via-gateway/`.

For current adapters whose active skill destination is `skills`, the lower-level common gateway mailbox skill SHALL continue to be available at `skills/mailbox/houmao-email-via-agent-gateway/`.

The round-oriented workflow skill SHALL:
- act as the default installed runtime-owned procedure for notifier-triggered shared mailbox processing rounds when a live gateway facade is available,
- define metadata-first triage, relevant-message selection, selective inspection, work execution, and post-success mark-read behavior for the current round,
- tell the agent to stop after the current round and wait for the next notification rather than proactively polling for more mail.

The common gateway skill SHALL:
- remain a lower-level protocol and reference skill for live discovery, check, read, send, reply, and mark-read behavior,
- continue to publish explicit resolver and endpoint guidance for the shared `/v1/mail/*` surface,
- support the round-oriented workflow skill rather than replacing it as the notifier-facing entrypoint.

Transport-specific mailbox skills such as `houmao-email-via-filesystem` and `houmao-email-via-stalwart` SHALL remain projected and SHALL narrow their ordinary guidance to transport validation, transport-specific context, and fallback behavior when the gateway facade is unavailable.

#### Scenario: Mailbox-enabled session receives processing, gateway, and transport runtime-owned skills
- **WHEN** the runtime starts a mailbox-enabled session
- **THEN** it projects `skills/mailbox/houmao-process-emails-via-gateway/` into the active skill destination
- **AND THEN** it also projects `skills/mailbox/houmao-email-via-agent-gateway/` and the runtime-owned mailbox skill for the active transport
- **AND THEN** the agent can discover all of those skills from the visible mailbox subtree without relying on hidden `.system` entries

#### Scenario: Houmao-owned mailbox skill naming requires explicit `houmao` invocation
- **WHEN** a runtime-owned mailbox skill is intended to be triggered through agent instructions
- **THEN** that skill uses a `houmao-<skillname>` name
- **AND THEN** the instruction text includes the keyword `houmao` when it intends to trigger that Houmao-owned skill
- **AND THEN** ordinary non-Houmao wording does not rely on implicit activation of the Houmao-owned skill

#### Scenario: Processing skill is treated as installed operational guidance for notifier rounds
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the runtime-owned `houmao-process-emails-via-gateway` skill is already projected into that session
- **AND THEN** notifier prompts may instruct the agent to use that installed skill directly for the current mailbox round

#### Scenario: Gateway mailbox skill remains the lower-level protocol reference
- **WHEN** an agent opens `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md`
- **THEN** that entry document continues to point the agent at lower-level action-specific subdocuments for resolver and `/v1/mail/*` operations
- **AND THEN** it does not replace the round-oriented processing workflow skill as the notifier-facing entrypoint

#### Scenario: Transport-specific mailbox skill narrows to transport context and fallback
- **WHEN** an agent opens `skills/mailbox/houmao-email-via-filesystem/SKILL.md` or `skills/mailbox/houmao-email-via-stalwart/SKILL.md`
- **THEN** that transport skill explains transport-specific constraints, references, and no-gateway fallback behavior
- **AND THEN** it points the agent at `skills/mailbox/houmao-email-via-agent-gateway/` and `skills/mailbox/houmao-process-emails-via-gateway/` for shared gateway mailbox workflow and operation guidance instead of duplicating both layers

## ADDED Requirements

### Requirement: Runtime-owned gateway email processing skill defines round-oriented notified email workflow
The system SHALL provide a projected runtime-owned mailbox skill `houmao-process-emails-via-gateway` that defines the workflow for processing gateway-notified unread emails in bounded rounds.

That workflow SHALL start from current unread metadata such as sender identity, subject, timestamps, and opaque message references before deciding which unread emails are relevant for the current round.

The workflow MAY use additional non-body metadata or lightweight gateway-visible detail to shortlist candidate emails, but it SHALL treat message-body inspection as a later step rather than as part of the initial reminder summary.

Once the workflow selects one or more task-relevant emails for the current round, it SHALL direct the agent to inspect all selected emails needed to decide and complete the work for that round.

The workflow SHALL direct the agent to perform the requested work before mutating read state.

The workflow SHALL direct the agent to mark only the successfully processed emails read at the end of that round.

The workflow SHALL leave unread emails that were deferred, skipped, or not completed in the unread set for later notifier-driven rounds.

After the agent completes the selected round of work, the workflow SHALL direct the agent to stop and wait for the next notifier wake-up rather than proactively checking for new mail on its own.

The workflow SHALL treat upstream gateway polling, unread snapshot updates, and mailbox-selection rules as outside the agent’s concern for that completed round.

#### Scenario: Metadata-first triage precedes message-body inspection
- **WHEN** the agent begins one notifier-driven email processing round
- **THEN** the workflow starts from current unread metadata such as sender, subject, timestamps, and opaque references
- **AND THEN** the agent does not need to inspect every unread message body before deciding which messages are relevant to the round

#### Scenario: Selected round-relevant emails are fully inspected before action
- **WHEN** the workflow selects one or more unread emails as relevant to the current round
- **THEN** the workflow directs the agent to inspect all selected emails needed to decide and perform the work for that round
- **AND THEN** the workflow does not require unrelated unread emails to be fully inspected first

#### Scenario: Successfully processed emails are marked read while deferred emails remain unread
- **WHEN** the agent completes work for some but not all unread emails during one round
- **THEN** the workflow directs the agent to mark only the successfully processed emails read
- **AND THEN** deferred or unfinished emails remain unread for later notifier-driven handling

#### Scenario: Completed round waits for the next notification
- **WHEN** the agent finishes the selected work for one email-processing round
- **THEN** the workflow directs the agent to stop rather than proactively polling for more mail
- **AND THEN** the agent waits for the next notifier-triggered wake-up to begin another round
