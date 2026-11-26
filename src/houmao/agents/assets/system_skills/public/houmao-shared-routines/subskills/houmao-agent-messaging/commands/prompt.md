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

# Prompt a Managed Agent (`prompt`)

## Workflow

1. **Confirm direct-turn authority and intent**: `prompt` submits a verbatim turn (`agent.prompt.direct`, requiring `agent-operator` or higher on keyed gateways). When a peer or caller holds `agent-requester` default authority or wants attributed task submission under the target's standing instructions, use [request.md](request.md) (`agents single ... request --text`) instead.
2. **Recover explicit target selector and `--prompt` text** (or piped stdin) from current prompt or recent stated context; ask before running if missing.
3. **Run `agents single ... prompt` or `agents self prompt`** (or pair-managed `POST /houmao/agents/{agent_ref}/requests`), adding optional `--model <name>` / `--reasoning-level <int>` only when requested and supported (`Codex` GPT-5.6 rejects `0`; `Kimi` indexes `support_efforts` from `1`, `0` turns thinking off where supported; `Claude` and `DSH` follow their adapter contracts).
4. **Report mode-specific delivery evidence**:
   - `tui`: terminal accepted input; provider turn completion remains observational (`gateway tui state|watch`).
   - `headless`: managed turn created/completed with durable `turn_id` artifacts.
   - `service` (`codex`, `kimi`, `dsh`): submitted over the persistent structured service request protocol (`request_id` inspectable via `/v1/control/service/requests/{request_id}`).
   - `web` (`kimi`, `dsh`): delivered to the bound Web/ACP session when ready; report busy/unavailable blockers without rerouting to another session.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the user request, then execute the plan.

## Command Shapes and Boundaries

```bash
<chosen houmao-mgr launcher> agents single --agent-name <name> prompt --prompt "<message>" [--port <pair-port>] [--model <m>] [--reasoning-level <n>]
<chosen houmao-mgr launcher> agents self prompt --prompt "<message>"
```

- Use [gateway-queue.md](gateway-queue.md) when explicit `--admission-policy ready-only|if-no-pending|always` gateway prompt control is requested.
- Keep `houmao-cccc` group chat (`houmao-cccc chat send|reply|pull`) separate from `prompt`; `houmao-cccc` routes through `/v1/plugins/{instance}/*` or `--direct-profile` rather than `agent.prompt.direct`.

## Guardrails

- DO NOT guess the target agent or prompt text, or route conversational turns through `gateway send-keys`.
- DO NOT silently downgrade a denied `prompt` to `request`, `--unsigned`, or `mail` without caller approval.
