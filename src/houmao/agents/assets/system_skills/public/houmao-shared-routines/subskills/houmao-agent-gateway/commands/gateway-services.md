---
metadata:
  skill_invocation_notation: >
    Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
    SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
    accepted only as legacy input when SKILL-MAIN.md is absent.
    Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
    `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
    `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
    subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
    by parent subcommand parent. Intermediate subcommands act as object generators.
    Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Use Gateway-Only Control and Plugin Services (`gateway-services`)

## Workflow

1. **Confirm gateway-specific scope**: use `houmao-shared-routines->houmao-agent-inspect` for generic read-only inspection and `houmao-shared-routines->houmao-agent-messaging` for transport-neutral `request`/`prompt`/`interrupt`; use `gateway-services` when operating gateway-only `/v1/control/*` surfaces or attached gateway plugins such as `houmao-cccc`.
2. **Verify live gateway attachment** via `agents single ... gateway status` or `agents self gateway status` when not already confirmed, recovering any missing target, prompt/key sequence, or plugin `--instance` before running commands.
3. **Execute the matching CLI or HTTP surface**:
   - **Scoped gateway CLI**: `agents single|self ... gateway {prompt|interrupt|send-keys}` and `gateway tui {state|history|watch|note-prompt}`.
   - **Mode-specific control HTTP** (see [../references/http-surface.md](../references/http-surface.md)): `headless` (`/v1/control/headless/{state,next-prompt-session}`), `service` (`/v1/control/service/{state,requests/{request_id}}`), `web` (`/v1/control/web/{state,history}`), and `tui` (`/v1/control/tui/{state,history,note-prompt}`).
   - **`houmao-cccc` gateway plugin CLI & routes**: run `houmao-cccc [--gateway-url <url>] [--signer-binding <json>] [--instance <id>] {binding,capabilities,discovery,members,connection,chat,mail}` (omitting `--gateway-url` inside verified managed self; using `--direct-profile <json>` + `--agent-id` only for direct Actor profile mode), backed by `/v1/plugins/{instance}/*` (`delivery`, `chat`, `mail`).
4. **Route signed custom JSON calls or mounts** to `houmao-shared-routines->houmao-agent-access->request()` and `houmao-shared-routines->houmao-agent-files`, and `/v1/mail/*` to `houmao-shared-routines->houmao-agent-email-comms`.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/http-surface.md](../references/http-surface.md) and the user request, then execute the plan.

## Representative Commands

```bash
# Gateway-only control and TUI tracking
<chosen houmao-mgr launcher> agents single --agent-id <id> gateway prompt --prompt "<text>" [--admission-policy ready-only|if-no-pending|always]
<chosen houmao-mgr launcher> agents single --agent-id <id> gateway send-keys --sequence "<keys>"
<chosen houmao-mgr launcher> agents self gateway tui state

# houmao-cccc plugin via verified managed self or explicit gateway
houmao-cccc binding
houmao-cccc members --group "$GROUP_ID"
houmao-cccc chat send --connection-token "$TOKEN" --to "$ACTOR_ID" --operation-id "$OP_ID" --text 'Ready for review.'
houmao-cccc chat reply --handle "$HANDLE" --operation-id "$REPLY_ID" --text 'Approved.'
houmao-cccc chat deliveries --handle "$HANDLE"
```

## Guardrails

- DO NOT silently replace explicit gateway control calls with transport-neutral `agents single|self prompt`, or use `send-keys` / `tui note-prompt` as ordinary prompt submission.
- DO NOT guess `{gateway.base_url}` or send unsigned HTTP to routes requiring verified caller proof, or conflate `houmao-cccc` plugin chat/mail with native Houmao `/v1/mail/*`.
