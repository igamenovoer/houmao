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

# Relaunch Agent Instance

## Workflow

1. **Distinguish `relaunch` from `refresh` and fresh `launch`**: use `native-resources` (`refresh --check` or `refresh`) when updating skills/MCP without restarting; use `relaunch` only when restarting or reviving an existing session's recorded identity, session root, built home, birth `--tmux-server` socket, and run mode.
2. **Resolve target scope**: use `agents self relaunch` only when clearly requested from inside the owning managed tmux session; otherwise require explicit `--agent-id` or `--agent-name` on `agents single`.
3. **Apply `--chat-session-mode` conservatively**: omit chat-session flags to honor the stored profile relaunch policy (or `new` default); pass `--chat-session-mode [new|tool_last_or_new|exact]` (plus `--chat-session-id <id>` for `exact`) only when explicitly requested.
4. **Run the `relaunch` command** and, when reviving a stopped record, state clearly that the existing managed-agent identity was revived on its recorded birth `--tmux-server` socket and run mode rather than freshly launched.
5. **Re-attach DSH ACP / Web gateway companions when needed**: if a relaunched DSH (`service` or `web` ACP-backed) session had an attached gateway companion whose live upstream session handle changed across relaunch, run `gateway detach` followed by `gateway attach` via `houmao-shared-routines->houmao-agent-gateway->lifecycle()` so the gateway re-binds the revived session cleanly.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the user request, then execute the plan.

## Command Shapes

```bash
<chosen houmao-mgr launcher> agents self relaunch [--chat-session-mode new|tool_last_or_new|exact] [--chat-session-id <id>]
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> relaunch [--port <pair-port>] [--chat-session-mode ...]
<chosen houmao-mgr launcher> agents single --agent-name <agent-name> relaunch [--port <pair-port>] [--chat-session-mode ...]
```

If relaunch posture or authority is unavailable for the target record, report the blocker without silently falling back to `project agents launch`.

## Guardrails

- DO NOT guess the target agent, silently substitute `project agents launch` when `relaunch` fails, or claim `relaunch` switches `--tmux-server` or run mode.
- DO NOT add `--chat-session-mode tool_last_or_new` or `exact` unless the caller explicitly asked to resume conversation state.
