# Houmao Agent Email Comms Skill Delta

## MODIFIED Requirements

### Requirement: `houmao-agent-email-comms` is the ordinary mailbox entrypoint
The system SHALL provide a projected runtime-owned Houmao skill named `houmao-agent-email-comms` as the single installed entrypoint for ordinary mailbox communication work.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
- manual mark for supported state changes,
- move among supported mailbox boxes where the binding permits ordinary placement changes,
- archive after processing where the binding supports ordinary archive.

`houmao-agent-email-comms` SHALL remain distinct from `houmao-process-emails-via-gateway`, which SHALL continue to own notifier-driven round workflow rather than ordinary mailbox operations.

#### Scenario: Mailbox-enabled session receives the unified ordinary mailbox skill
- **WHEN** the runtime starts a mailbox-enabled session for a supported tool
- **THEN** the visible Houmao-owned mailbox skill surface includes `houmao-agent-email-comms`
- **AND THEN** the agent uses that skill as the ordinary entrypoint for status, list, peek, read, send, post, reply, mark, move, archive, or resolve-live work that the selected binding supports
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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When current prompt or recent mailbox context already provides the exact current `gateway.base_url`, the skill SHALL use that value directly for shared `/v1/mail/*` operations.

When current prompt or recent mailbox context does not provide the exact live gateway endpoint, the skill SHALL direct the agent to `houmao-mgr agents self mail resolve-live` for the current managed session or `houmao-mgr agents single --agent-name|--agent-id ... mail resolve-live` for a selected managed agent.

When the resolved mailbox binding reports no live gateway facade, the skill SHALL direct the agent to the supported no-gateway fallback surface for the active transport instead of guessing a gateway endpoint.

The skill SHALL continue to treat `message_ref` and `thread_ref` as opaque shared-mailbox references across all of those actions.

The skill SHALL direct ordinary state and placement actions according to the selected binding's capabilities. On protected bindings, backend placement control SHALL apply to shared gateway calls, manager fallback, and direct transport access.

#### Scenario: Context-provided gateway URL avoids redundant discovery
- **WHEN** an agent follows `houmao-agent-email-comms` for shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context already provides the exact current gateway base URL
- **THEN** the skill uses that context-provided base URL as the endpoint prefix for `/v1/mail/*`
- **AND THEN** it does not require the agent to rerun manager-based discovery first

#### Scenario: No-gateway session uses the fallback surface
- **WHEN** an agent follows `houmao-agent-email-comms` for ordinary mailbox work
- **AND WHEN** `houmao-mgr agents self mail resolve-live` reports `gateway: null`
- **THEN** the skill directs the agent to the supported fallback surface for the resolved transport
- **AND THEN** it does not guess a localhost port or invent a direct shared-gateway endpoint

#### Scenario: Archive action is the ordinary completion reference
- **WHEN** an agent follows `houmao-agent-email-comms` after successfully processing a message on a binding that supports ordinary archive
- **THEN** the skill directs the agent to the `archive` action for completion
- **AND THEN** it describes `mark-read` as a read-state change

#### Scenario: Ordinary agent work uses a protected binding

- **WHEN** an agent processes mail on a protected binding
- **THEN** the skill directs the agent to reply when appropriate and leave filing to the backend under independent mailbox-owner authority
- **AND THEN** the agent completes the task without ordinary archive, move, or placement-changing mark
- **AND THEN** binding restrictions apply to every ordinary path, including no-gateway fallback

### Requirement: `houmao-agent-email-comms` uses direct scoped command snippets for managed-agent mail fallback commands
The packaged `houmao-agent-email-comms` skill SHALL document supported managed-agent mail fallback commands as direct fenced `bash` snippets or equivalent explicit command shapes.

At minimum, covered fallback commands SHALL include `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`.

For bindings that permit ordinary move, the skill SHALL document fallback mail move with the current destination option:

```bash
houmao-mgr agents self mail move --message-ref <message_ref> --destination-box <box>
```

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL NOT reference `houmao-mgr internals command-templates`, command-template ids, template blockers, or command-template support when explaining managed-agent mail fallback commands.

#### Scenario: Fallback move uses destination-box
- **WHEN** a user asks the skill to move a mailbox message to another box on a binding that permits ordinary move without a live gateway facade
- **THEN** the skill guidance shows `mail move --message-ref <message_ref> --destination-box <box>`
- **AND THEN** it does not show the stale `mail move --message-ref <message_ref> --box <box>` command shape
