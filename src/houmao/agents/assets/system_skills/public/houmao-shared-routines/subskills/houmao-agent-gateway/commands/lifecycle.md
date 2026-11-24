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

# Manage Live Gateway Lifecycle

Use this action when the gateway itself needs to be attached, detached, or inspected from outside the attached agent session.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and requested lifecycle action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target or clear action, ask the user in Markdown before proceeding.
4. Use `attach` to start or reuse the live gateway sidecar for an already-running managed agent. Keep the foreground default unless the user requests background execution. For private deployment settings, see [Deployment Configuration](#deployment-configuration).
5. Use `detach` to stop the live gateway while leaving the session gateway-capable for later reattach.
6. Use `status` when the caller first needs to confirm whether the session is gateway-capable, not attached, or currently live.
7. Run `agents single ... gateway attach|detach|status` for selected-agent CLI lifecycle work, or `agents self gateway attach|detach|status` for current-session CLI lifecycle work.
8. If the caller is already operating through the pair-managed HTTP API, use the matching `/houmao/agents/{agent_ref}/gateway` lifecycle routes instead of direct `/v1/...`.
9. Report whether the gateway is attached now, the current `gateway_health`, the live host and port when present, and any foreground execution metadata returned by status.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Command Shapes

Run direct scoped lifecycle commands:

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway attach
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway detach
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway status
<chosen houmao-mgr launcher> agents self gateway status
```

For tmux-backed managed sessions, these attach forms use foreground same-session auxiliary-window execution when supported. The managed-agent surface remains tmux window `0`; the live gateway sidecar uses a non-zero auxiliary tmux window. Treat returned `execution_mode` and `gateway_tmux_window_index` from status or attach output as authoritative; do not infer topology from tmux window names or ordering.

Use `--gateway-tui-watch-poll-interval-seconds`, `--gateway-tui-stability-threshold-seconds`, `--gateway-tui-completion-stability-seconds`, `--gateway-tui-unknown-to-stalled-timeout-seconds`, `--gateway-tui-stale-active-recovery-seconds`, or `--gateway-tui-final-stable-active-recovery-seconds` only when the user explicitly asks to tune gateway TUI tracking timing or safeguard timing. Values are positive seconds and affect the attached gateway sidecar, not the managed agent's foreground/background posture.

Pair-managed lifecycle routes:

- `POST /houmao/agents/{agent_ref}/gateway/attach`
- `POST /houmao/agents/{agent_ref}/gateway/detach`
- `GET /houmao/agents/{agent_ref}/gateway`

## Deployment Configuration

Run deployment changes in the selected agent's execution-owner context. Pass `--access-config` to read private JSON for listener bind, advertisement, public input, or the configured administrator signer. Relative paths resolve from the selected agent's owner-side working directory.

```bash
houmao-mgr agents single --agent-id "$AGENT_ID" gateway attach --access-config "$ACCESS_CONFIG"
houmao-mgr agents single --agent-id "$AGENT_ID" gateway attach --plugins-config "$PLUGINS_CONFIG"
```

Use `--plugins-config` for the gateway's versioned YAML or JSON plugin selection. The packages must be installed in the gateway's environment. Omitting this flag reuses the persisted selection. An explicitly empty selection clears it on the next attach. The flags can be combined when both settings are part of the same requested attach.

An equivalent configuration can reuse a live gateway. Changed deployment or plugin settings require an explicit gateway detach and attach. The agent body can keep running. For retained policy, grants, and live administrator roster changes, use `houmao-shared-routines->houmao-agent-access`. For native skill and MCP freshness, use `houmao-shared-routines->houmao-agent-instance->native-resources()`.

## Guardrails

- DO NOT use this action to launch or stop the managed agent process; use `houmao-shared-routines->houmao-agent-instance` for that.
- DO NOT use `--pair-port` on `agents self gateway ...`; it belongs only to selected-agent pair-authority targeting.
- DO NOT describe `--pair-port` as the live gateway listener port; it selects Houmao pair authority only.
- DO NOT assume attach succeeds just because the session is gateway-capable.
- DO NOT confuse detached offline status with permanent loss of gateway capability.
- DO NOT choose `--background` by default; background gateway execution is an explicit user override, not the normal attach posture.
- DO NOT add `--gateway-tui-*` timing overrides unless the user asked for custom TUI tracking or safeguard timings.
- DO NOT add background or gateway TUI timing flags unless the user explicitly asked for them.
- DO NOT copy private deployment documents or signer material into shared output.
