# houmao-agent-email-comms-skill Specification

## Purpose
Give managed agents one skill for ordinary mailbox work. Route actions through the gateway or a supported fallback, and provide filesystem and Stalwart guidance where the selected transport requires it.
## Requirements
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

The skill's `SKILL-MAIN.md`, `commands/resolve-live.md`, `commands/status.md`, and `references/endpoint-contract.md` SHALL use the selected channel's effective capabilities and `expected_binding_id`. The `archive`, `move`, and `mark` action pages and `references/managed-agent-fallback.md` SHALL explain which operations require placement authority. Ordinary read and answered flags SHALL remain distinct from changes to archived state or folder membership.

The endpoint reference SHALL document binding-scoped send, reply, post, and owner-file attachment permissions under the Write Permissions anchor used by the action pages. It SHALL describe sender-address blocking and direct Archive placement as recipient backend rules for new deliveries. An ordinary sender SHALL use its own binding irrespective of the recipient's gateway role or whether the recipient gateway is attached. Mail rule administration SHALL route to the independently authorized mailbox-owner workflow.

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

#### Scenario: A Sender Uses Ordinary Mail Independently of Gateway Access

- **WHEN** a caller with a verified sender binding needs to email a peer
- **THEN** the skill uses that sender binding and the selected transport's authority for submission or deposit
- **AND THEN** it explains that the recipient's backend applies its rules to new deliveries and reports the same sender-facing acceptance for Inbox and Archive placement

### Requirement: `houmao-agent-email-comms` internalizes transport-specific guidance

`houmao-agent-email-comms` SHALL keep filesystem-specific and Stalwart-specific guidance in its own transport references. The projected routine SHALL keep ordinary transport usage under the unified skill.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Filesystem guidance SHALL cover mailbox-local rules, disk layout, and mailbox view validation when relevant. `references/transports/filesystem.md` SHALL explain that a trusted writer owns recipient placement on protected offline bindings.

Stalwart guidance SHALL cover current resolver fields, exact origin trust, credential handling limits, independent channel selection, and direct-access constraints when relevant. `references/transports/stalwart.md` and `references/stalwart-resolver-fields.md` SHALL route online binding administration to `houmao-mailbox-mgr` and distinguish ordinary mailbox access from separately authorized policy application and owner filing. Both transport references SHALL qualify archive, move, and archived-state marking by the current binding's placement authority.

#### Scenario: Filesystem-specific mailbox question stays inside the unified skill

- **WHEN** the current mailbox transport is `filesystem`
- **AND WHEN** the task needs mailbox-local rules, layout, or no-gateway fallback detail
- **THEN** the agent finds that guidance inside `houmao-agent-email-comms`
- **AND THEN** it uses the protected binding's authorized writer path when applicable

#### Scenario: Stalwart-specific fallback stays inside the unified skill

- **WHEN** the current mailbox transport is `stalwart`
- **AND WHEN** the task needs transport-local fallback guidance after gateway discovery
- **THEN** the agent finds that guidance inside `houmao-agent-email-comms` and retains the original online binding
- **AND THEN** it can follow the existing owner-managed handoff for operations that require independent authority

### Requirement: `houmao-agent-email-comms` teaches reply-enabled operator-origin post default
The packaged `houmao-agent-email-comms` skill SHALL describe operator-origin `post` as reply-enabled by default.

That skill SHALL explain that callers may omit reply-policy input for the default `operator_mailbox` behavior, and SHALL present `reply_policy=none` as the explicit no-reply opt-out.

The skill SHALL NOT describe default operator-origin post behavior as one-way or no-reply.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When showing gateway-backed post examples, the skill SHALL either omit `reply_policy` or set it to `operator_mailbox` for the default case.

When showing manager CLI post examples, the skill SHALL either omit `--reply-policy` or use `--reply-policy operator_mailbox` for the default case, and SHALL reserve `--reply-policy none` for explicit no-reply examples.

#### Scenario: Skill user sees reply-enabled default
- **WHEN** an agent opens the `houmao-agent-email-comms` operator-origin post action guidance
- **THEN** the skill explains that operator-origin posts default to replies through `HOUMAO-operator@houmao.localhost`
- **AND THEN** it identifies `reply_policy=none` as the way to request a one-way operator-origin note

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

Examples in `references/managed-agent-fallback.md` and `references/scoped-cli.md` SHALL pin the resolved channel and binding. `archive`, `move`, and `mark` examples that change archived state SHALL apply only when the binding and caller allow the action. A placement refusal SHALL preserve the operation outcome and selected binding.

#### Scenario: Fallback move uses destination-box
- **WHEN** a user asks the skill to move a mailbox message to another box on a binding that permits ordinary move without a live gateway facade
- **THEN** the skill guidance shows `mail move --message-ref <message_ref> --destination-box <box>`
- **AND THEN** it does not show the stale `mail move --message-ref <message_ref> --box <box>` command shape

### Requirement: Mail skill explains conditional attachment authority
The mail skill SHALL explain that a gateway send, reply, or post requires its corresponding action on the selected mailbox binding. It SHALL describe `mail.attachment.owner_file` as an additional action required on that binding when the gateway request includes owner-file attachments.

#### Scenario: Basic mail write carries no attachments
- **WHEN** the caller sends, replies, or posts a text-only message
- **THEN** the skill describes the selected binding's ordinary mail action as the relevant gateway permission
- **AND THEN** it leaves the existing authorized no-gateway fallback available where supported

#### Scenario: Mail write includes an owner-file attachment
- **WHEN** the caller sends, replies, or posts with an owner-file attachment
- **THEN** the skill explains that the caller also needs `mail.attachment.owner_file` on the same channel and binding
- **AND THEN** it directs the caller to the maintained access workflow for any required grant

### Requirement: Mail writes use their receipts and read-only follow-ups

The bundled mail guidance SHALL use the first compact CLI receipt to report a send, reply, or post. Its action pages and `references/scoped-cli.md` SHALL use `mail peek` for additional details on the binding that owns the top-level `message_ref` and read-only evidence for uncertain writes. Sender receipts SHALL preserve the transport's result without disclosing the recipient's rules or placement.

#### Scenario: The first write is verified

- **WHEN** a managed agent receives a verified send, reply, or post receipt and only needs confirmation
- **THEN** the skill reports the receipt's status and reference from the first call
- **AND THEN** it describes online send confirmation as provider-confirmed submission and offline send confirmation as transport-confirmed deposit

#### Scenario: The agent inspects send or reply details

- **WHEN** a managed agent needs more information about a verified send or reply
- **THEN** the skill shows `mail peek --message-ref` on the writing agent's original channel and binding
- **AND THEN** the guidance selects JSON on the first write or the read-only inspection

#### Scenario: The operator inspects a post

- **WHEN** an authorized caller needs more information about a verified post
- **THEN** the skill directs it to peek using the selected recipient's channel, binding, and receipt reference

#### Scenario: A send or reply remains unresolved

- **WHEN** a managed agent receives a submission-only or uncertain send or reply result without a verified reference
- **THEN** the skill directs it to check `mail list --box sent` using the sender's authority and original channel and binding when available
- **AND THEN** it retains an unresolved outcome if the lookup is inconclusive

#### Scenario: An operator post remains unresolved

- **WHEN** an authorized caller needs to reconcile a post with an uncertain outcome
- **THEN** the skill directs it to inspect the same target binding's Inbox and any Archive view it is authorized to read
- **AND THEN** it retains an unresolved outcome if the lookup is inconclusive

### Requirement: Ordinary email skill covers recipient inbound policy, Stalwart JMAP trust, and compact receipts
`houmao-agent-email-comms` SHALL document private backend placement and prospective delivery rules. It SHALL preserve Stalwart JMAP discovery, origin trust, Inbox/Sent/Archive readiness, and scoped receipt verification.

#### Scenario: Peer mail encounters recipient policy or Stalwart intranet discovery
- **WHEN** a managed agent sends ordinary mail to a peer or uses an attached Stalwart online channel
- **THEN** `houmao-agent-email-comms` explains that the backend files matching new deliveries directly in Archive even while the recipient gateway is stopped, and directs `mailbox online` setup to `houmao-mailbox-mgr`
- **AND THEN** `references/transports/stalwart.md` and `references/endpoint-contract.md` cover JMAP origin trust, Inbox/Sent/Archive readiness, and how to inspect a reply on the original binding using the CLI `message_ref` or HTTP `message.message_ref`
- **AND THEN** the receipt distinguishes offline deposit from provider submission and leaves recipient placement private

### Requirement: Ordinary email skill removes duplicate boilerplate and aligns mark and move command links
`houmao-agent-email-comms/SKILL-MAIN.md` SHALL eliminate duplicated caller-classification prose between `## Workflow` and `## Actor Frame Gate`, strip Missing-Input boilerplate, back `mark` and `move` in `## Subcommands` with dedicated `commands/mark.md` and `commands/move.md` pages (each with `## Workflow`), and keep `peek` and `read` explicitly routed to the shared `commands/read.md` page.

#### Scenario: Entrypoint and command pages align across all mailbox operations
- **WHEN** a reviewer inspects `houmao-agent-email-comms`
- **THEN** caller classification appears once in `## Actor Frame Gate` without redundant boilerplate in `SKILL-MAIN.md`
- **AND THEN** every command in `manifest.toml` links cleanly to a conforming command page (dedicated `commands/<cmd>.md` pages for `resolve-live`, `status`, `list`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, with `peek` sharing `commands/read.md`)

### Requirement: Ordinary email skill preserves channel separation, binding pinning, and pagination invariants
`houmao-agent-email-comms` SHALL distinguish admin `post` from agent `self mail`. It SHALL teach channel separation, binding pins from `resolve-live`, reconciliation of `authoritative: false`, bounded schema v3 pagination, `content_complete` checks, and `mail.attachment.owner_file`. Ordinary archive follows successful required replies where the binding permits it. Protected bindings reserve filing for the independently authorized mailbox owner.

#### Scenario: Cross-channel address translation and unpinned mutations remain prohibited
- **WHEN** an agent operates on dual offline and online bindings
- **THEN** it never bridges channels or guesses addresses across `offline` and `online`, pins `expected_binding_id` on every channel-scoped lifecycle call, and omits `include_body` from `/v1/mail/{channel}/list`
