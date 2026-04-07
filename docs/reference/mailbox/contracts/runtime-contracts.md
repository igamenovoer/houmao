# Mailbox Runtime Contracts

This page explains the runtime-owned contract around mailbox configuration, manifest-backed bindings, projected skills, and `agents mail` request and result handling.

## Mental Model

The runtime is the authority for mailbox attachment to a session.

- Declarative config or CLI overrides choose the mailbox transport and identity.
- The runtime resolves that into one `MailboxResolvedConfig`.
- The session manifest persists that resolved mailbox binding as the durable mailbox authority reused by resume and gateway transport access.
- The runtime projects the mailbox system skill into the built brain home under a visible tool-native flat Houmao-owned skill surface: Claude and Codex use top-level `skills/houmao-.../`, while Gemini uses top-level `.gemini/skills/houmao-.../`.
- Later mailbox work resolves current bindings through `pixi run houmao-mgr agents mail resolve-live` instead of assuming the provider process's inherited mailbox env snapshot is still current.
- That same command is also the runtime-owned discovery path for the attached shared-mailbox gateway facade: when a valid live gateway is attached it returns a `gateway` object with `base_url`, `host`, `port`, `protocol_version`, and `state_path`; otherwise it returns `gateway: null`.

## Declarative And Resolved Config

The declarative mailbox payload supports these fields:

- `transport`
- `principal_id`
- `address`
- `filesystem_root`

Current rules:

- `transport` is required when `mailbox` is present.
- `filesystem` and `stalwart` are implemented in v1.
- If `principal_id` is omitted, the runtime derives one from the tool, role, and optional agent identity.
- If `address` is omitted, it defaults to `<principal_id>@agents.localhost`.
- If `filesystem_root` is omitted in maintained project-aware flows, it defaults to `<active-overlay>/mailbox`, bootstrapping `<cwd>/.houmao/mailbox` when no overlay exists yet; `HOUMAO_GLOBAL_MAILBOX_DIR` or an explicit `filesystem_root` override still wins when supplied.
- `stalwart` bindings resolve from either `base_url` or explicit `jmap_url` plus `management_url`.
- Persisted `stalwart` bindings remain secret-free and store `credential_ref` instead of inline credentials.

Representative resolved payload:

```json
{
  "transport": "filesystem",
  "principal_id": "HOUMAO-research",
  "address": "HOUMAO-research@agents.localhost",
  "filesystem_root": "/abs/path/tmp/shared-mail",
  "bindings_version": "2026-03-13T09:15:30.123456Z"
}
```

That persisted `launch_plan.mailbox` payload is also the durable mailbox capability contract reused by resume, refresh, and gateway-side integrations. The gateway mail transport uses that durable manifest-backed capability rather than persisting a second mailbox copy under `gateway/`.

## Manager-Owned `resolve-live` Contract

`pixi run houmao-mgr agents mail resolve-live` is the supported current-mailbox discovery surface.

Top-level fields:

- `source`
- `transport`
- `principal_id`
- `address`
- `bindings_version`
- `mailbox`
- `gateway`
- `gateway_available`
- `managed_agent`

Filesystem-specific fields:

- `mailbox.filesystem.root`
- `mailbox.filesystem.sqlite_path`
- `mailbox.filesystem.mailbox_path`
- `mailbox.filesystem.local_sqlite_path`
- `mailbox.filesystem.inbox_path`
- `mailbox.filesystem.mailbox_kind`

Stalwart-specific fields:

- `mailbox.stalwart.jmap_url`
- `mailbox.stalwart.management_url`
- `mailbox.stalwart.login_identity`
- `mailbox.stalwart.credential_ref`
- `mailbox.stalwart.credential_file`

Important rules:

- Treat the persisted manifest mailbox payload as durable authority and the resolver output as the current actionable mailbox contract.
- Resolve current mailbox bindings through `pixi run houmao-mgr agents mail resolve-live` before direct attached-session mailbox work. Inside the owning tmux session, selectors may be omitted. Outside tmux, or when targeting a different agent, use `--agent-id` or `--agent-name`.
- Mailbox-specific shell export is not part of the supported runtime contract.
- Treat `mailbox.filesystem.root` as authoritative.
- `mailbox.filesystem.sqlite_path` remains the shared mailbox-root `index.sqlite` catalog.
- `mailbox.filesystem.mailbox_path` resolves the current mailbox-view directory for the addressed mailbox.
- `mailbox.filesystem.local_sqlite_path` is the authoritative mailbox-view SQLite database for the current mailbox.
- `mailbox.filesystem.inbox_path` follows the active mailbox registration, so it may resolve through a symlinked `mailboxes/<address>` entry into a private directory.
- If `bindings_version` changes, discard cached assumptions and reload the current bindings.
- `mailbox.stalwart.credential_file` is session-local secret material derived from the persisted secret-free `credential_ref`.

## Shared Catalog Versus Mailbox-Local State

The filesystem transport splits durable state between a shared catalog and mailbox-local mailbox-view state.

- The shared mailbox-root `index.sqlite` keeps registrations, canonical message catalog data, projections, delivery metadata, attachment metadata, and other structural state shared across the mailbox root.
- Each resolved mailbox directory owns `mailbox.sqlite`, which keeps mailbox-view state that can differ per mailbox, including read or unread, starred, archived, deleted, and mailbox-local thread summaries.
- Inside `mailbox.sqlite`, `message_state` rows are keyed by `message_id` and mailbox-local `thread_summaries` rows are keyed by `thread_id`.
- Because the database is already scoped to one resolved mailbox directory, mailbox-local rows do not need `registration_id` as part of their primary identity.
- Shared-root unread counters are no longer authoritative for mailbox-view state once mailbox-local SQLite exists.

## Projected Skill Contract

The runtime projects one shared Houmao gateway skill plus one transport-specific mailbox skill into the brain home during brain build. The primary discoverable mailbox skill surface is tool-specific:

- Claude native runtime homes: `skills/houmao-process-emails-via-gateway/SKILL.md`, `skills/houmao-email-via-agent-gateway/SKILL.md`, `skills/houmao-email-via-filesystem/SKILL.md`, and `skills/houmao-email-via-stalwart/SKILL.md`
- Codex runtime homes: `skills/houmao-process-emails-via-gateway/SKILL.md`, `skills/houmao-email-via-agent-gateway/SKILL.md`, `skills/houmao-email-via-filesystem/SKILL.md`, and `skills/houmao-email-via-stalwart/SKILL.md`
- Gemini runtime homes: `.gemini/skills/houmao-process-emails-via-gateway/SKILL.md`, `.gemini/skills/houmao-email-via-agent-gateway/SKILL.md`, `.gemini/skills/houmao-email-via-filesystem/SKILL.md`, and `.gemini/skills/houmao-email-via-stalwart/SKILL.md`

For Claude, these mailbox skills live under the isolated runtime-owned `CLAUDE_CONFIG_DIR` and not under the launched workdir's `.claude/skills/` tree.
For Gemini, Houmao-owned projection now targets `.gemini/skills/...`, and `.agents/skills/...` is only Gemini's upstream alias surface.

Shared runtime rules:

- require `houmao-mgr agents mail resolve-live` for tmux-backed same-session discovery,
- prefer the live gateway `/v1/mail/*` facade for shared mailbox operations when the resolver returns a live `gateway.base_url`,
- otherwise use `houmao-mgr agents mail check|send|reply|mark-read`,
- treat `message_ref` as the shared reply and mark-read target contract,
- treat `authoritative: false` as submission-only rather than mailbox truth,
- present `rules/` as markdown policy guidance and `rules/scripts/` as compatibility or implementation detail rather than the ordinary workflow contract.

Filesystem-specific rules:

- inspect `rules/README.md` and `rules/protocols/filesystem-mailbox-v1.md` for policy or repair guidance,
- do not require ordinary attached-session mailbox work to invoke mailbox-owned scripts under `rules/scripts/`,
- treat `mailbox.filesystem.local_sqlite_path` as the source of truth for mailbox-view read or unread and thread-summary state.

Stalwart-specific rules:

- use the current `mailbox.stalwart.*` fields returned by the resolver for direct transport access when no live gateway mailbox facade is available,
- do not assume filesystem mailbox rules, SQLite paths, locks, or projection symlinks exist for this transport.

## Managed `agents mail` Contract

Public subcommands:

- `resolve-live`
- `status`
- `check`
- `send`
- `reply`
- `mark-read`

Selector rules:

- explicit `--agent-id` or `--agent-name` wins,
- inside the owning managed tmux session, omitted selectors resolve the current session through `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` fallback second,
- outside tmux without selectors, the command fails explicitly,
- `--port` is only supported with an explicit selector.

Argument rules:

- `check` accepts `--unread-only`, `--limit`, and `--since`.
- `send` requires at least one `--to`, a `--subject`, and exactly one of `--body-file` or `--body-content`.
- `reply` requires `--message-ref` and exactly one of `--body-file` or `--body-content`.
- `send` and `reply` accept repeatable `--attach`.
- `mark-read` requires `--message-ref`.
- Recipients must be full mailbox addresses, not short names.

Result-strength rules:

- verified pair-owned or manager-owned execution returns `authoritative: true`, `status: "verified"`, and `execution_path: "gateway_backed"` or `"manager_direct"`,
- local live-TUI fallback returns `authoritative: false`, `execution_path: "tui_submission"`, and submission-only status such as `submitted`, `rejected`, `busy`, `interrupted`, or `tui_error`,
- callers must verify non-authoritative outcomes through manager-owned `status` or `check`, gateway `/v1/mail/*` state, filesystem mailbox inspection, or transport-native mailbox state.

```mermaid
sequenceDiagram
    participant CLI as agents mail
    participant RT as Runtime
    participant MB as Gateway facade<br/>or transport
    participant Ses as Live session
    CLI->>RT: resolve target and authority
    alt Direct or gateway-backed authority available
        RT->>MB: execute mailbox operation
        MB-->>RT: verified mailbox result
        RT-->>CLI: authoritative=true
    else Local TUI fallback only
        RT->>Ses: structured mailbox prompt
        Ses-->>RT: submission result<br/>and optional preview
        RT-->>CLI: authoritative=false
    end
```

## Low-Level Runtime Prompt Contract

The raw runtime module `pixi run python -m houmao.agents.realm_controller mail ...` still exists as the structured prompt-turn surface behind local fallback and lower-level testing. Those low-level runtime commands remain TUI-mediated surfaces and return submission-oriented envelopes rather than claiming mailbox truth on their own.

Representative submission result:

```json
{
  "address": "HOUMAO-research@agents.localhost",
  "authoritative": false,
  "execution_path": "tui_submission",
  "operation": "send",
  "request_id": "mailreq-20260313T091530Z-3c9f1e6ab2",
  "principal_id": "HOUMAO-research",
  "schema_version": 1,
  "status": "submitted",
  "transport": "filesystem",
  "verification_required": true
}
```

When the runtime does recover a preview payload, it still validates that preview against the active `request_id`, `operation`, and mailbox binding before surfacing it under `preview_result`, but the command does not require that preview to return.

## Source References

- [`src/houmao/agents/mailbox_runtime_models.py`](../../../../src/houmao/agents/mailbox_runtime_models.py)
- [`src/houmao/agents/mailbox_runtime_support.py`](../../../../src/houmao/agents/mailbox_runtime_support.py)
- [`src/houmao/agents/system_skills.py`](../../../../src/houmao/agents/system_skills.py)
- [`src/houmao/agents/realm_controller/cli.py`](../../../../src/houmao/agents/realm_controller/cli.py)
- [`src/houmao/agents/realm_controller/mail_commands.py`](../../../../src/houmao/agents/realm_controller/mail_commands.py)
- [`src/houmao/agents/brain_builder.py`](../../../../src/houmao/agents/brain_builder.py)
- [`src/houmao/agents/assets/system_skills/houmao-email-via-agent-gateway/SKILL.md`](../../../../src/houmao/agents/assets/system_skills/houmao-email-via-agent-gateway/SKILL.md)
- [`src/houmao/agents/assets/system_skills/houmao-email-via-filesystem/SKILL.md`](../../../../src/houmao/agents/assets/system_skills/houmao-email-via-filesystem/SKILL.md)
- [`src/houmao/agents/assets/system_skills/houmao-email-via-filesystem/references/env-vars.md`](../../../../src/houmao/agents/assets/system_skills/houmao-email-via-filesystem/references/env-vars.md)
- [`src/houmao/agents/assets/system_skills/houmao-email-via-stalwart/SKILL.md`](../../../../src/houmao/agents/assets/system_skills/houmao-email-via-stalwart/SKILL.md)
- [`src/houmao/agents/assets/system_skills/houmao-email-via-stalwart/references/env-vars.md`](../../../../src/houmao/agents/assets/system_skills/houmao-email-via-stalwart/references/env-vars.md)
