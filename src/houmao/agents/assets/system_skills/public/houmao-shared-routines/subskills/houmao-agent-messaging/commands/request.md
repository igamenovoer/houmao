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

# Submit an Attributed Work Request (`request`)

## Workflow

1. **Confirm target selector and task `--text`**: require explicit `--agent-id` or `--agent-name` (plus remote trusted coordinates or `--passive-url` when applicable) and required `--text <task>` from the caller's prompt or stated context.
2. **Select caller attribution**:
   - **Inside a verified managed session**: omit `--source-agent-id` and `--unsigned` so `houmao-mgr` signs automatically with the current managed session's configured peer signer.
   - **From an execution owner acting for a local owned source agent**: pass `--source-agent-id <owned-source-agent-id>` (the source agent can be stopped).
   - **Anonymous caller**: pass `--unsigned` only when anonymous submission under the target's `default-group` is explicitly intended.
3. **Select target transport coordinates**:
   - Verified local target with attached gateway: omit `--url` and `--passive-url`.
   - Remote live gateway: pass `--url <trusted-gateway-url>` alongside `--context-id`, `--generation`, `--presence`, and optional `--ca-bundle <file>` from trusted deployment/discovery records.
   - Qualified passive-managed detached target (such as detached DSH Headless/Service via passive listener): pass `--passive-url <trusted-passive-listener>` with the required target coordinates.
4. **Execute `houmao-mgr agents single ... request`** and report the admission result or refusal verbatim; if the target is offline and asynchronous delivery is wanted instead, route to [mail.md](mail.md) (`houmao-shared-routines->houmao-agent-email-comms`) only with caller intent.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the user request, then execute the plan.

## Command Shapes and Permission Semantics

```bash
# Automatic current managed-session peer signing (default inside a managed agent)
<chosen houmao-mgr launcher> agents single --agent-id "$TARGET_ID" request --text 'Review the migration plan.'

# Owner-selected local source signer or remote/passive target coordinates
<chosen houmao-mgr launcher> agents single --agent-id "$TARGET_ID" request \
  --text 'Review the migration plan.' \
  [--source-agent-id "$SOURCE_ID" | --unsigned] \
  [--url "$GATEWAY_URL" --context-id "$CTX" --generation "$GEN" --presence "$PRESENCE" [--ca-bundle "$CA_FILE"]] \
  [--passive-url "$PASSIVE_URL"]
```

- **Quoted task framing (`agent.request.submit`)**: Houmao wraps `--text` as attributed task content under the target agent's existing instructions (for example, `--text '/clear'` arrives as quoted request text rather than executing a native slash command, which requires `agent-operator` direct command authority).
- **Policy evaluation**: keyed targets initially give eligible fallback callers `agent-requester`. A verified caller with only an exact status grant and disabled fallback lacks `agent.request.submit`. Explicit `--unsigned` follows the target's separate anonymous policy. Manage grants via `houmao-shared-routines->houmao-agent-access`.

## Guardrails

- DO NOT retry a refused or failed signed `request` with `--unsigned`, `prompt`, `send-keys`, or `mail` unless the caller explicitly authorizes changing attribution or channel.
- DO NOT omit required `--text` or guess `--url`, `--passive-url`, `--context-id`, `--generation`, or `--presence` coordinates.
