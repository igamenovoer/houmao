# Mailbox Quickstart

This page shows the shortest safe path to a working mailbox-enabled session and the three runtime-owned mailbox commands you will use first: `mail check`, `mail send`, and `mail reply`.

## Choose Your Transport

Choose the transport before you copy a startup example.

| Transport | Use this when | Start here |
| --- | --- | --- |
| `filesystem` | you want the fully Houmao-owned mailbox transport with local rules, SQLite state, and projections | stay on this page |
| `stalwart` | you want Stalwart to be the mailbox authority for delivery, unread state, and reply ancestry | [Stalwart Setup And First Session](operations/stalwart-setup-and-first-session.md) |

The rest of this page keeps the shortest inline filesystem example. The `mail check`, `mail send`, and `mail reply` CLI surface is shared, but Stalwart-specific startup and secret-handling guidance lives in the dedicated page above.

## Mental Model

You do not wire mailbox behavior into prompts by hand. The runtime does three jobs for you:

1. Resolve one mailbox binding for the session.
2. Bootstrap or validate the selected transport binding and register or provision the session address.
3. Project the runtime-owned mailbox skill and env vars into the session so later `mail` commands can reuse the same binding. The visible `skills/mailbox/...` subtree is the primary mailbox skill surface, and `skills/.system/mailbox/...` remains a compatibility mirror.

After that, `mail check`, `mail send`, and `mail reply` run against a resumed session. The CLI talks to the runtime, the runtime prompts the session using the projected mailbox skill for the selected transport, and the session returns one structured result payload.

## Filesystem Quickstart

You can enable mailbox support from declarative brain config or from `start-session` overrides. In v1, the implemented transports are `filesystem` and `stalwart`.

Implicit filesystem mailbox state now defaults to `~/.houmao/mailbox`, independently from the runtime root. `AGENTSYS_GLOBAL_MAILBOX_DIR` relocates that shared mailbox area for CI or controlled environments, and an explicit `--mailbox-root` override still wins for one launch.

```bash
pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest <runtime-root>/manifests/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend claude_headless \
  --mailbox-transport filesystem \
  --mailbox-root tmp/shared-mail \
  --mailbox-principal-id AGENTSYS-research \
  --mailbox-address AGENTSYS-research@agents.localhost
```

The `start-session` result includes a redacted mailbox payload in the session manifest output when mailbox support is enabled.

```json
{
  "mailbox": {
    "transport": "filesystem",
    "principal_id": "AGENTSYS-research",
    "address": "AGENTSYS-research@agents.localhost",
    "filesystem_root": "/abs/path/tmp/shared-mail",
    "bindings_version": "2026-03-13T09:15:30.123456Z"
  }
}
```

Workspace-local job dirs remain separate from mailbox state. When the runtime uses local job storage under `<working-directory>/.houmao/jobs/<session-id>/`, that `.houmao/` tree is a scratch area rather than the shared mailbox root and is a good candidate for ignore rules in local repos.

```mermaid
sequenceDiagram
    participant Op as Operator
    participant CLI as start-session
    participant RT as Runtime
    participant FS as Mailbox<br/>root
    participant Ses as Session
    Op->>CLI: start-session<br/>with mailbox flags
    CLI->>RT: resolve effective<br/>mailbox config
    RT->>FS: bootstrap root<br/>and register address
    RT->>Ses: launch with mailbox env<br/>and projected skill
    RT-->>CLI: session manifest<br/>with redacted mailbox
```

## Check Mail

Use `mail check` against a resumed mailbox-enabled session.

```bash
pixi run python -m houmao.agents.realm_controller mail check \
  --agent-identity AGENTSYS-research \
  --unread-only \
  --limit 10
```

Important details:

- `--agent-identity` can be a name or a manifest path, using the normal runtime control-target rules.
- `--unread-only` and `--limit` are optional filters.
- `--since` accepts an RFC3339 lower bound when you want incremental review.

Typical stdout is structured JSON returned by the session through the runtime-owned mailbox contract.

```json
{
  "ok": true,
  "operation": "check",
  "principal_id": "AGENTSYS-research",
  "transport": "filesystem",
  "unread_count": 2
}
```

## Send Mail

```bash
pixi run python -m houmao.agents.realm_controller mail send \
  --agent-identity AGENTSYS-research \
  --to AGENTSYS-orchestrator@agents.localhost \
  --subject "Investigate parser drift" \
  --body-file body.md \
  --attach notes.txt
```

Important details:

- `--to` is required and may be repeated.
- `--cc` is optional and may be repeated.
- Recipients must be full mailbox addresses such as `AGENTSYS-orchestrator@agents.localhost`.
- Exactly one of `--body-file` or `--body-content` must be supplied.
- `--attach` paths are validated by the CLI before they are surfaced to the session.

## Reply To Mail

```bash
pixi run python -m houmao.agents.realm_controller mail reply \
  --agent-identity AGENTSYS-research \
  --message-ref filesystem:msg-20260312T050000Z-parent \
  --body-content "Reply with next steps"
```

Important details:

- `--message-ref` is required.
- `--message-id` remains accepted as a compatibility alias.
- Exactly one of `--body-file` or `--body-content` must be supplied.
- Attachments are allowed on replies too.
- Replies target the shared opaque `message_ref` contract; do not derive behavior from transport-prefixed values embedded inside the ref.

## What The Runtime Expects From The Session

Every `mail` command uses the runtime-owned projected mailbox skill for the selected transport and expects exactly one sentinel-delimited JSON result payload back from the session.

- Filesystem sessions use `skills/mailbox/email-via-filesystem/SKILL.md` as the primary mailbox skill document and may also carry the same content at `skills/.system/mailbox/email-via-filesystem/SKILL.md` as a compatibility mirror.
- Stalwart sessions use `skills/mailbox/email-via-stalwart/SKILL.md` as the primary mailbox skill document and may also carry the same content at `skills/.system/mailbox/email-via-stalwart/SKILL.md` as a compatibility mirror.
- When a live loopback gateway is attached, shared mailbox operations prefer the gateway `/v1/mail/*` facade before falling back to direct transport-specific access.
- For bounded attached-session turns, that shared facade now includes `POST /v1/mail/state` so one processed unread target can be marked read without reconstructing transport-local identifiers.

```mermaid
sequenceDiagram
    participant Op as Operator
    participant CLI as mail send<br/>or reply
    participant RT as Runtime
    participant Ses as Session
    participant MB as Gateway facade<br/>or transport
    Op->>CLI: run mail command
    CLI->>RT: resume session<br/>and build request
    RT->>Ses: prompt with mailbox skill<br/>plus JSON contract
    Ses->>MB: use live gateway facade<br/>or direct transport path
    Ses-->>RT: one sentinel-delimited<br/>JSON result
    RT-->>CLI: parsed JSON stdout
```

## When To Leave Quickstart

- If you are using the `stalwart` transport, continue with [Stalwart Setup And First Session](operations/stalwart-setup-and-first-session.md).
- If you need the exact message schema, go to [Canonical Model](contracts/canonical-model.md).
- If you need the exact env vars or request/result envelopes, go to [Runtime Contracts](contracts/runtime-contracts.md).
- If you need stepwise operational guidance, go to [Common Workflows](operations/common-workflows.md).

## Source References

- [`src/houmao/agents/realm_controller/cli.py`](../../../src/houmao/agents/realm_controller/cli.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/agents/mailbox_runtime_support.py`](../../../src/houmao/agents/mailbox_runtime_support.py)
- [`src/houmao/agents/realm_controller/mail_commands.py`](../../../src/houmao/agents/realm_controller/mail_commands.py)
- [`src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-filesystem/SKILL.md`](../../../src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-filesystem/SKILL.md)
- [`src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-stalwart/SKILL.md`](../../../src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-stalwart/SKILL.md)
