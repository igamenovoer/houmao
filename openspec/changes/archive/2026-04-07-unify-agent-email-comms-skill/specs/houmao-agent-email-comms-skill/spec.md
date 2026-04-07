## ADDED Requirements

### Requirement: `houmao-agent-email-comms` is the ordinary mailbox entrypoint
The system SHALL provide a projected runtime-owned Houmao skill named `houmao-agent-email-comms` as the single installed entrypoint for ordinary mailbox communication work.

That skill SHALL cover ordinary mailbox operations across supported mailbox transports, including:

- current mailbox discovery,
- mailbox status inspection,
- unread or current-message inspection,
- message selection guidance,
- outbound send,
- reply,
- post-success mark-read behavior.

`houmao-agent-email-comms` SHALL remain distinct from `houmao-process-emails-via-gateway`, which SHALL continue to own notifier-driven round workflow rather than ordinary mailbox operations.

#### Scenario: Mailbox-enabled session receives the unified ordinary mailbox skill
- **WHEN** the runtime starts a mailbox-enabled session for a supported tool
- **THEN** the visible Houmao-owned mailbox skill surface includes `houmao-agent-email-comms`
- **AND THEN** the agent uses that skill as the ordinary entrypoint for status, check, read, send, reply, or mark-read work
- **AND THEN** notifier-driven mailbox rounds continue to use `houmao-process-emails-via-gateway`

### Requirement: `houmao-agent-email-comms` routes shared gateway and fallback mailbox actions
`houmao-agent-email-comms` SHALL organize ordinary mailbox operations through internal action pages or equivalent internal subdocuments rather than through separate top-level installed mailbox skills.

At minimum, the unified skill SHALL provide internal guidance for:

- `resolve-live`
- `status`
- `check`
- `read`
- `send`
- `reply`
- `mark-read`

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

### Requirement: `houmao-agent-email-comms` internalizes transport-specific guidance
`houmao-agent-email-comms` SHALL keep filesystem-specific and Stalwart-specific guidance as internal transport pages, sections, or references within the same skill package.

The runtime SHALL NOT require separate top-level installed skill names for filesystem or Stalwart ordinary mailbox guidance once `houmao-agent-email-comms` is projected.

Filesystem-specific guidance within the unified skill SHALL cover mailbox-local rules, on-disk layout, and mailbox-view validation only when those details are relevant to the current task.

Stalwart-specific guidance within the unified skill SHALL cover current `mailbox.stalwart.*` resolver fields, credential-handling limits, and direct-access constraints only when those details are relevant to the current task.

#### Scenario: Filesystem-specific mailbox question stays inside the unified skill
- **WHEN** the current mailbox transport is `filesystem`
- **AND WHEN** the task needs mailbox-local rules, layout, or no-gateway fallback detail
- **THEN** the agent finds that guidance inside `houmao-agent-email-comms`
- **AND THEN** the runtime does not rely on a separate top-level installed filesystem mailbox skill

#### Scenario: Stalwart-specific fallback stays inside the unified skill
- **WHEN** the current mailbox transport is `stalwart`
- **AND WHEN** the task needs transport-local fallback guidance after gateway discovery
- **THEN** the agent finds that guidance inside `houmao-agent-email-comms`
- **AND THEN** the runtime does not rely on a separate top-level installed Stalwart mailbox skill
