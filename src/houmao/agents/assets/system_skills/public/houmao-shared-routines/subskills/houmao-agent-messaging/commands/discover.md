---
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

# Discover Managed-Agent Messaging Capability

Use this action when you need to identify the correct managed agent first or discover whether current gateway and mailbox handoff surfaces are available.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target selector is still missing, ask the user in Markdown before proceeding.
4. If the request is generic read-only inspection rather than messaging preparation, hand it off to `houmao-shared-routines->houmao-agent-inspect`.
5. Run `agents single --agent-name <name> state` first to confirm the managed-agent identity and current operational summary.
6. If the current task may need ordinary prompting, live gateway control, or any other gateway-preferred prompt routing decision, run `agents single --agent-name <name> gateway status` next.
7. If the current task may need mailbox work or an exact live gateway base URL, run `agents single --agent-name <name> mail resolve-live` next.
8. When the caller is already operating through the pair-managed HTTP API instead of the CLI, use the managed-agent routes summarized in `references/managed-agent-http.md`.
9. Report the target identity plus only the capability facts that matter for the next action: gateway availability, mailbox availability, exact `gateway.base_url` when present, and whether prompt or outgoing mailbox work should prefer a gateway-backed surface.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shapes

Use:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> state
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway status
<chosen houmao-mgr launcher> agents single --agent-name <name> mail resolve-live
```

Authoritative selector alternatives:

- `--agent-id <id>`
- `--agent-id <id>` at the `agents single` group level
- `--port <pair-port>` for `agents single ... state` and `agents single ... mail resolve-live`
- `--pair-port <pair-port>` for `agents single ... gateway status`

Managed-agent HTTP discovery surfaces:

- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

## Guardrails

- Do not guess the target managed agent when the selector is missing or ambiguous.
- Do not keep generic liveness, log, artifact, or tmux inspection on this discovery action once it is clear the request is not about a messaging follow-up.
- Do not scrape tmux state directly when the managed-agent discovery surfaces already exist.
- Do not assume a gateway is attached just because the agent is currently running.
- Do not assume mailbox capability from the provider, role, or specialist name alone.
- Do not keep using stale capability assumptions across turns when the task depends on current live gateway or mailbox state.
