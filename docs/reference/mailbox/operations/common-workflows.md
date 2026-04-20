# Mailbox Common Workflows

This page explains the practical v1 procedures for bootstrapping a mailbox, resolving current bindings, listing and reading mail, sending mail, posting operator-origin notes, replying, archiving processed mail, and deciding when filesystem rules or compatibility helpers need deeper inspection.

## Mental Model

The safest workflow is simple:

1. Let the runtime create or validate the mailbox root.
2. Treat `rules/` as the mailbox-local operating manual, not as an ordinary execution protocol.
3. Resolve the current live mailbox binding through `houmao-mgr agents mail resolve-live`.
4. Prefer the live gateway `/v1/mail/*` facade when it is attached.
5. Otherwise use `houmao-mgr agents mail list|peek|read|send|post|reply|mark|move|archive`.
6. Touch `rules/scripts/` only for compatibility, debugging, or repair workflows that intentionally bypass the ordinary managed path.

## Bootstrap And First Inspection

For the preferred local serverless workflow:

1. `pixi run houmao-mgr mailbox init --mailbox-root <path>`
2. `pixi run houmao-mgr agents launch ...` or `pixi run houmao-mgr agents join ...`
3. `pixi run houmao-mgr agents mailbox register --agent-name <name> --mailbox-root <path>`

After bootstrap, inspect these first when you are new to a mailbox root or are recovering an environment:

- `<mailbox_root>/rules/README.md`
- `<mailbox_root>/rules/protocols/filesystem-mailbox-v1.md`

If you intentionally need compatibility helpers for repair or debugging, inspect `<mailbox_root>/rules/scripts/requirements.txt` at that point, not as part of every ordinary mailbox turn.

```mermaid
sequenceDiagram
    participant Op as Operator
    participant CLI as houmao-mgr
    participant RT as Runtime
    participant FS as Mailbox<br/>root
    Op->>CLI: mailbox init
    CLI->>FS: bootstrap root
    Op->>CLI: agents launch or join
    CLI->>RT: create or adopt session
    Op->>CLI: agents mailbox register
    RT->>FS: register address and persist binding
    Op->>CLI: agents mail resolve-live
    CLI-->>Op: normalized binding and optional gateway
```

## Resolve Live Bindings

Use `resolve-live` whenever you need the exact current binding set or the exact live shared-mailbox gateway endpoint.

```bash
pixi run houmao-mgr agents mail resolve-live --agent-name research
```

Important details:

- Inside the owning managed tmux session, selectors may be omitted.
- Outside tmux, or when targeting a different agent, use `--agent-id` or `--agent-name`.
- When the returned payload includes `gateway.base_url`, that is the supported discovery path for attached `/v1/mail/*` work instead of ad hoc host or port guessing.

## Read Mail Safely

Use `agents mail list` when you want manager-owned or gateway-backed mailbox reads.

```bash
pixi run houmao-mgr agents mail list \
  --agent-name research \
  --read-state unread \
  --limit 10
```

Operational guidance:

- Re-resolve current bindings when you switch shells, sessions, or long-running automation contexts.
- Treat `mailbox.filesystem.local_sqlite_path` as the source of truth for unread versus read state and mailbox-local thread summaries.
- Treat `mailbox.filesystem.sqlite_path` as the shared structural catalog, not as the mailbox-view read or unread authority.
- Use `agents mail peek` when you need the body without changing read state; use `agents mail read` when you intentionally want to inspect the body and mark it read.
- Archive a message only after the mailbox action or processing step has completed successfully.
- If a manager fallback result is `authoritative: false`, verify with `agents mail list`, filesystem inspection, or transport-native mailbox state.

## Send New Mail

Use `agents mail send` for manager-owned composition.

```bash
pixi run houmao-mgr agents mail send \
  --agent-name research \
  --to orchestrator@houmao.localhost \
  --subject "Investigate parser drift" \
  --body-file body.md \
  --attach notes.txt
```

Stepwise expectations:

1. The CLI validates attachment paths and body source.
2. Houmao resolves current mailbox authority for the target managed agent.
3. If a live loopback gateway mailbox facade is attached, shared mailbox operations use that gateway route.
4. Otherwise Houmao uses manager-owned direct execution when it can prove authority.
5. Only when direct authority is unavailable does the local live TUI fallback submit a mailbox prompt into the session.
6. Submission-only fallback results require separate verification.

## Post Operator-Origin Mail

Use `agents mail post` when the operator wants to deliver an operator-origin note into the managed agent mailbox without sending as the managed mailbox principal.

```bash
pixi run houmao-mgr agents mail post \
  --agent-name research \
  --subject "Resume after sync" \
  --body-content "Continue from the latest mailbox checkpoint."
```

Operator-origin guidance:

- `post` is filesystem-only in v1. A `stalwart` binding rejects it explicitly.
- The canonical sender is always `HOUMAO-operator@houmao.localhost`.
- Managed-agent defaults use `<agentname>@houmao.localhost`, while `HOUMAO-*` locals under `houmao.localhost` are reserved for Houmao-owned system mailboxes.
- `post` requires authoritative mailbox execution and never falls back to TUI prompt submission.
- `reply_policy=operator_mailbox` is the default and routes replies to that operator-origin thread back to `HOUMAO-operator@houmao.localhost`.
- `reply_policy=none` is the explicit no-reply opt-out and replies to those operator-origin messages are rejected explicitly.
- This receive-side behavior is reply-only for reply-enabled operator-origin messages, not a general free-send contract for the reserved system mailbox.

## Reply And Archive

Use `agents mail reply` when you already know the parent shared `message_ref`.

```bash
pixi run houmao-mgr agents mail reply \
  --agent-name research \
  --message-ref filesystem:msg-20260312T050000Z-parent \
  --body-content "Reply with next steps"
```

After you successfully process one nominated message, archive that same `message_ref`:

```bash
pixi run houmao-mgr agents mail archive \
  --agent-name research \
  --message-ref filesystem:msg-20260312T050000Z-parent
```

Reply and archive guidance:

- Treat `message_ref` as opaque even when it contains a transport-prefixed value such as `filesystem:...` or `stalwart:...`.
- When a live gateway facade is attached, use the shared gateway routines for `list`, `peek`, `read`, `reply`, `mark`, `move`, and `archive`.
- When the manager-owned fallback path is in use, `houmao-mgr agents mail read` is the supported explicit read acknowledgement command and `houmao-mgr agents mail archive` is the supported processed-work closeout command.
- Replies to operator-origin parent messages succeed when the parent was posted with `reply_policy=operator_mailbox`, which is the default for new operator-origin posts.
- If `archive` returns `authoritative: false`, verify through `agents mail list`, filesystem inspection, or transport-native mailbox state before assuming the message was archived.

## Answered Archive Lifecycle

The filesystem mailbox tracks an `answered` state on each message, independent of `read`. When a message is marked answered, it moves to an `answered/` archive lane, keeping the active inbox clean without deleting processed messages.

The `answered` flag is a per-recipient mutable state field stored in `index.sqlite`, alongside `read`, `starred`, `archived`, and `deleted`. The gateway mail-notifier filters use `answered_state` when resolving the eligible inbox set (both `any_inbox` and `unread_only` modes accept any answered state by default).

Marking a message answered is a separate action from marking it read. A message can be read but not yet answered, or answered without being explicitly marked read first. Use the answered state when the processing workflow has a distinct "reply sent" or "action taken" stage that should remove the message from further notification-driven wakeup cycles without archiving it in the broader sense.

## When `rules/` Inspection Is Mandatory

Inspect mailbox-local `rules/` before:

- running direct filesystem repair or recovery work,
- invoking compatibility Python helpers from `rules/scripts/`,
- touching `index.sqlite`,
- touching any `.lock` file,
- assuming a layout detail that could be mailbox-local policy rather than transport-wide policy.

If managed `rules/scripts/` assets are missing, treat that as a bootstrap or initialization problem, not a prompt to author replacement scripts in place.

## Source References

- [`src/houmao/srv_ctrl/commands/agents/mail.py`](../../../../src/houmao/srv_ctrl/commands/agents/mail.py)
- [`src/houmao/srv_ctrl/commands/managed_agents.py`](../../../../src/houmao/srv_ctrl/commands/managed_agents.py)
- [`src/houmao/agents/realm_controller/mail_commands.py`](../../../../src/houmao/agents/realm_controller/mail_commands.py)
- [`src/houmao/agents/mailbox_runtime_support.py`](../../../../src/houmao/agents/mailbox_runtime_support.py)
- [`src/houmao/mailbox/assets/rules/README.md`](../../../../src/houmao/mailbox/assets/rules/README.md)
- [`src/houmao/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md`](../../../../src/houmao/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md)
- [`src/houmao/mailbox/managed.py`](../../../../src/houmao/mailbox/managed.py)
