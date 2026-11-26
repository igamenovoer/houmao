# Spec Delta

## ADDED Requirements

### Requirement: Ordinary email skill covers recipient inbound policy, Stalwart JMAP trust, and compact receipts
`houmao-agent-email-comms` SHALL document recipient inbound mail policy (`agent-requester` default vs `agent-observer` denial evaluated at recipient transport), Stalwart intranet online mail JMAP discovery and origin trust (`--trust-jmap-origin`, Inbox/Sent/Archive readiness in `references/transports/stalwart.md`), and compact write receipts (`message_ref` + `peek`).

#### Scenario: Peer mail encounters recipient policy or Stalwart intranet discovery
- **WHEN** a managed agent sends ordinary mail to a peer or uses an attached Stalwart online channel
- **THEN** `houmao-agent-email-comms` explains recipient-side policy evaluation independent of recipient live gateway state, and directs `mailbox online` setup issues to `houmao-mailbox-mgr`
- **AND THEN** `references/transports/stalwart.md` and `references/endpoint-contract.md` cover JMAP origin trust, Inbox/Sent/Archive readiness, and `message_ref` receipt verification

### Requirement: Ordinary email skill removes duplicate boilerplate and aligns mark and move command links
`houmao-agent-email-comms/SKILL-MAIN.md` SHALL eliminate duplicated caller-classification prose between `## Workflow` and `## Actor Frame Gate`, strip Missing-Input boilerplate, back `mark` and `move` in `## Subcommands` with dedicated `commands/mark.md` and `commands/move.md` pages (each with `## Workflow`), and keep `peek` and `read` explicitly routed to the shared `commands/read.md` page.

#### Scenario: Entrypoint and command pages align across all mailbox operations
- **WHEN** a reviewer inspects `houmao-agent-email-comms`
- **THEN** caller classification appears once in `## Actor Frame Gate` without redundant boilerplate in `SKILL-MAIN.md`
- **AND THEN** every command in `manifest.toml` links cleanly to a conforming command page (dedicated `commands/<cmd>.md` pages for `resolve-live`, `status`, `list`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, with `peek` sharing `commands/read.md`)

### Requirement: Ordinary email skill preserves channel separation, binding pinning, and pagination invariants
`houmao-agent-email-comms` SHALL preserve admin `post` vs agent `self mail`, strict `offline`/`online` channel separation, `resolve-live` -> `expected_binding_id` pinning, `authoritative: false` confirmation, `schema_version: 3` finite pagination without `include_body`, `content_complete` checks, `mail.attachment.owner_file`, and archive-after-reply.

#### Scenario: Cross-channel address translation and unpinned mutations remain prohibited
- **WHEN** an agent operates on dual offline and online bindings
- **THEN** it never bridges channels or guesses addresses across `offline` and `online`, pins `expected_binding_id` on every call, and omits `include_body` from `/v1/mail/{channel}/list`
