## MODIFIED Requirements

### Requirement: Runtime-owned mailbox skill projection separates gateway operations from transport-specific guidance and uses Houmao-owned skill naming
The system SHALL project a round-oriented runtime-owned mailbox workflow skill for gateway-notified email processing into every mailbox-enabled session in addition to the lower-level common gateway mailbox skill and the active transport-specific mailbox skill.

Projected Houmao-owned mailbox skills SHALL use a `houmao-<skillname>` naming convention under the visible mailbox subtree so runtime-owned Houmao skills are distinguishable from role-authored or third-party skill names.

That `houmao-<skillname>` convention SHALL also define the activation boundary for Houmao-owned skills: the instruction text must include the keyword `houmao` when it intends to trigger a Houmao-owned skill.

For current adapters whose active skill destination is `skills`, the round-oriented workflow skill SHALL be available at `skills/mailbox/houmao-process-emails-via-gateway/`.

For current adapters whose active skill destination is `skills`, the lower-level common gateway mailbox skill SHALL continue to be available at `skills/mailbox/houmao-email-via-agent-gateway/`.

The round-oriented workflow skill SHALL:
- act as the default installed runtime-owned procedure for notifier-triggered shared mailbox processing rounds when a live gateway facade is available,
- assume the notifier round already provides the exact current gateway base URL,
- define gateway-API-first metadata triage, unread-listing, relevant-message selection, selective inspection, work execution, and post-success mark-read behavior for the current round,
- tell the agent to stop after the current round and wait for the next notification rather than proactively polling for more mail.

The common gateway skill SHALL:
- remain a lower-level protocol and reference skill for live discovery, status, check, send, reply, and mark-read behavior,
- use a gateway base URL already present in prompt/context when that URL is available,
- fall back to `houmao-mgr agents mail resolve-live` only when the current gateway base URL cannot be determined from prompt/context,
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

#### Scenario: Gateway mailbox skill reuses context-provided base URL before falling back to manager discovery
- **WHEN** an agent opens `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md`
- **AND WHEN** the current prompt or recent mailbox context already provides the exact gateway base URL
- **THEN** that skill tells the agent to use the context-provided gateway URL directly
- **AND THEN** it does not require the agent to rerun manager discovery first

#### Scenario: Transport-specific mailbox skill narrows to transport context and fallback
- **WHEN** an agent opens `skills/mailbox/houmao-email-via-filesystem/SKILL.md` or `skills/mailbox/houmao-email-via-stalwart/SKILL.md`
- **THEN** that transport skill explains transport-specific constraints, references, and no-gateway fallback behavior
- **AND THEN** it points the agent at `skills/mailbox/houmao-email-via-agent-gateway/` and `skills/mailbox/houmao-process-emails-via-gateway/` for shared gateway mailbox workflow and operation guidance instead of duplicating both layers

### Requirement: Runtime-owned gateway email processing skill defines round-oriented notified email workflow
The system SHALL provide a projected runtime-owned mailbox skill `houmao-process-emails-via-gateway` that defines the workflow for processing gateway-notified unread emails in bounded rounds.

That workflow SHALL assume the current notifier round already provides the exact current gateway base URL needed for shared mailbox operations.

The workflow SHALL start by using the shared gateway mailbox API itself to inspect current mailbox state for the round, including listing unread mail through the shared `/v1/mail/*` surface.

That workflow SHALL start from current unread metadata such as sender identity, subject, timestamps, and opaque message references before deciding which unread emails are relevant for the current round.

The workflow MAY use additional non-body metadata or lightweight gateway-visible detail to shortlist candidate emails, but it SHALL treat message-body inspection as a later step rather than as part of notifier-owned prompt content.

Once the workflow selects one or more task-relevant emails for the current round, it SHALL direct the agent to inspect all selected emails needed to decide and complete the work for that round.

The workflow SHALL direct the agent to perform the requested work before mutating read state.

The workflow SHALL direct the agent to mark only the successfully processed emails read at the end of that round.

The workflow SHALL leave unread emails that were deferred, skipped, or not completed in the unread set for later notifier-driven rounds.

After the agent completes the selected round of work, the workflow SHALL direct the agent to stop and wait for the next notifier wake-up rather than proactively checking for new mail on its own.

The workflow SHALL treat upstream gateway polling, unread snapshot updates, and mailbox-selection rules as outside the agent’s concern for that completed round.

If the gateway base URL is missing from the notifier round context, the workflow SHALL treat that as a contract failure for the current round rather than silently switching to manager-based rediscovery.

#### Scenario: Metadata-first triage follows an agent-run unread listing step
- **WHEN** the agent begins one notifier-driven email processing round
- **THEN** the workflow directs the agent to inspect current unread mail through the shared gateway mailbox API
- **AND THEN** the workflow starts triage from current unread metadata such as sender, subject, timestamps, and opaque references
- **AND THEN** the agent does not need notifier-rendered unread summaries to start the round

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

#### Scenario: Missing base URL is treated as a notifier-round contract failure
- **WHEN** the agent begins the notifier-driven workflow for one round
- **AND WHEN** the current round context does not provide the gateway base URL
- **THEN** the workflow does not silently switch to manager-based rediscovery for that round
- **AND THEN** the missing gateway bootstrap is treated as a contract failure for the current wake-up

### Requirement: Runtime-owned mailbox skills use the manager-owned live resolver as the ordinary gateway discovery contract
Projected runtime-owned mailbox skills SHALL direct agents to the manager-owned live resolver `houmao-mgr agents mail resolve-live` only when current prompt/context does not already provide the exact current gateway base URL needed for shared `/v1/mail/*` mailbox operations.

When current prompt/context already provides the exact current gateway base URL, runtime-owned mailbox skills SHALL treat that URL as the authoritative endpoint prefix for the current mailbox work and SHALL NOT require redundant manager-based rediscovery.

When the manager-owned live resolver returns a `gateway` object, runtime-owned mailbox skills SHALL treat `gateway.base_url` as the exact current endpoint prefix for shared `/v1/mail/*` mailbox operations.

Projected runtime-owned mailbox skills SHALL NOT present `pixi run houmao-mgr agents mail resolve-live` as part of ordinary mailbox operation workflow.

Projected runtime-owned mailbox skills SHALL NOT present `python -m houmao.agents.mailbox_runtime_support resolve-live` as part of the ordinary mailbox operation workflow.

#### Scenario: Gateway mailbox skill obtains the current endpoint from prompt context when available
- **WHEN** an agent follows the runtime-owned gateway mailbox skill for shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context already provides the exact current gateway base URL
- **THEN** the skill uses that context-provided base URL as the endpoint prefix for `/v1/mail/*`
- **AND THEN** the agent does not need to rerun manager-based discovery first

#### Scenario: Gateway mailbox skill falls back to `houmao-mgr agents mail resolve-live`
- **WHEN** an agent follows the runtime-owned gateway mailbox skill for shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context does not provide the exact current gateway base URL
- **THEN** the skill directs the agent to run `houmao-mgr agents mail resolve-live`
- **AND THEN** the agent obtains the exact live mailbox endpoint from the returned `gateway.base_url`

#### Scenario: Runtime-owned mailbox skills avoid `pixi` and direct Python-module resolver guidance
- **WHEN** an agent follows the projected mailbox skills for ordinary mailbox work
- **THEN** those skills do not instruct the agent to use `pixi run houmao-mgr agents mail resolve-live`
- **AND THEN** they do not instruct the agent to invoke `python -m houmao.agents.mailbox_runtime_support resolve-live` directly
