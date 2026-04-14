## MODIFIED Requirements

### Requirement: `houmao-agent-email-comms` is the ordinary mailbox entrypoint
The system SHALL provide a projected runtime-owned Houmao skill named `houmao-agent-email-comms` as the single installed entrypoint for ordinary mailbox communication work.

That skill SHALL cover ordinary mailbox operations across supported mailbox transports, including:

- current mailbox discovery,
- mailbox status inspection,
- list and open-work inspection,
- non-mutating message peek,
- mutating message read,
- message selection guidance,
- outbound send,
- operator-origin post where supported,
- reply,
- manual mark,
- move among supported mailbox boxes,
- archive-after-processing behavior.

`houmao-agent-email-comms` SHALL remain distinct from `houmao-process-emails-via-gateway`, which SHALL continue to own notifier-driven round workflow rather than ordinary mailbox operations.

#### Scenario: Mailbox-enabled session receives the unified ordinary mailbox skill
- **WHEN** the runtime starts a mailbox-enabled session for a supported tool
- **THEN** the visible Houmao-owned mailbox skill surface includes `houmao-agent-email-comms`
- **AND THEN** the agent uses that skill as the ordinary entrypoint for status, list, peek, read, send, post, reply, mark, move, archive, or resolve-live work
- **AND THEN** notifier-driven mailbox rounds continue to use `houmao-process-emails-via-gateway`

### Requirement: `houmao-agent-email-comms` routes shared gateway and fallback mailbox actions
`houmao-agent-email-comms` SHALL organize ordinary mailbox operations through internal action pages or equivalent internal subdocuments rather than through separate top-level installed mailbox skills.

At minimum, the unified skill SHALL provide internal guidance for:

- `resolve-live`
- `status`
- `list`
- `peek`
- `read`
- `send`
- `post`
- `reply`
- `mark`
- `move`
- `archive`

When current prompt or recent mailbox context already provides the exact current `gateway.base_url`, the skill SHALL use that value directly for shared `/v1/mail/*` operations.

When current prompt or recent mailbox context does not provide the exact live gateway endpoint, the skill SHALL direct the agent to `houmao-mgr agents mail resolve-live`.

When the resolved mailbox binding reports no live gateway facade, the skill SHALL direct the agent to the supported no-gateway fallback surface for the active transport instead of guessing a gateway endpoint.

The skill SHALL continue to treat `message_ref` and `thread_ref` as opaque shared-mailbox references across all of those actions.

#### Scenario: Context-provided gateway URL avoids redundant discovery
- **WHEN** an agent follows `houmao-agent-email-comms` for shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context already provides the exact current gateway base URL
- **THEN** the skill uses that context-provided base URL as the endpoint prefix for `/v1/mail/*`
- **AND THEN** it does not require the agent to rerun manager-based discovery first

#### Scenario: No-gateway session uses the fallback surface
- **WHEN** an agent follows `houmao-agent-email-comms` for ordinary mailbox work
- **AND WHEN** `houmao-mgr agents mail resolve-live` reports `gateway: null`
- **THEN** the skill directs the agent to the supported fallback surface for the resolved transport
- **AND THEN** it does not guess a localhost port or invent a direct shared-gateway endpoint

#### Scenario: Archive action is the ordinary completion reference
- **WHEN** an agent follows `houmao-agent-email-comms` after successfully processing a mailbox message
- **THEN** the skill directs the agent to the `archive` action for completion
- **AND THEN** it does not present `mark-read` as the processed-mail completion action
