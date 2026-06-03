## MODIFIED Requirements

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

When current prompt or recent mailbox context does not provide the exact live gateway endpoint, the skill SHALL direct the agent to `houmao-mgr agents self mail resolve-live` for the current managed session or `houmao-mgr agents single --agent-name|--agent-id ... mail resolve-live` for a selected managed agent.

When the resolved mailbox binding reports no live gateway facade, the skill SHALL direct the agent to the supported no-gateway fallback surface for the active transport instead of guessing a gateway endpoint.

The skill SHALL continue to treat `message_ref` and `thread_ref` as opaque shared-mailbox references across all of those actions.

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
- **WHEN** an agent follows `houmao-agent-email-comms` after successfully processing a mailbox message
- **THEN** the skill directs the agent to the `archive` action for completion
- **AND THEN** it does not present `mark-read` as the processed-mail completion action

## REMOVED Requirements

### Requirement: `houmao-agent-email-comms` uses CLI-owned templates for managed-agent mail fallback commands
**Reason**: The command-template renderer has been retired; managed-agent mail fallback commands are documented directly in the packaged skill.

**Migration**: Use direct scoped `houmao-mgr agents self mail ...` and `houmao-mgr agents single ... mail ...` command snippets.

#### Scenario: Fallback commands no longer use template rendering
- **WHEN** the skill has selected fallback CLI mail for one turn
- **THEN** it shows a direct scoped mail command
- **AND THEN** command shape is not loaded from a command-template registry

## ADDED Requirements

### Requirement: `houmao-agent-email-comms` uses direct scoped command snippets for managed-agent mail fallback commands
The packaged `houmao-agent-email-comms` skill SHALL document supported managed-agent mail fallback commands as direct fenced `bash` snippets or equivalent explicit command shapes.

At minimum, covered fallback commands SHALL include `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`.

The skill SHALL document fallback mail move with the current destination option:

```bash
houmao-mgr agents self mail move --message-ref <message_ref> --destination-box <box>
```

The skill SHALL NOT reference `houmao-mgr internals command-templates`, command-template ids, template blockers, or command-template support when explaining managed-agent mail fallback commands.

#### Scenario: Fallback move uses destination-box
- **WHEN** a user asks the skill to move a mailbox message to another box without a live gateway facade
- **THEN** the skill guidance shows `mail move --message-ref <message_ref> --destination-box <box>`
- **AND THEN** it does not show the stale `mail move --message-ref <message_ref> --box <box>` command shape
