# Manage Live Gateway Lifecycle

Use this action when the gateway itself needs to be attached, detached, or inspected from outside the attached agent session.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and requested lifecycle action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target or clear action, ask the user in Markdown before proceeding.
4. Use `attach` to start or reuse the live gateway sidecar for an already-running managed agent.
5. Use `detach` to stop the live gateway while leaving the session gateway-capable for later reattach.
6. Use `status` when the caller first needs to confirm whether the session is gateway-capable, not attached, or currently live.
7. If the caller is already operating through the pair-managed HTTP API, use the matching `/houmao/agents/{agent_ref}/gateway` lifecycle routes instead of direct `/v1/...`.
8. Report whether the gateway is attached now, the current `gateway_health`, the live host and port when present, and any foreground execution metadata returned by status.

## Command Shapes

Attach:

```text
<chosen houmao-mgr launcher> agents gateway attach --agent-name <name>
<chosen houmao-mgr launcher> agents gateway attach --agent-id <id>
<chosen houmao-mgr launcher> agents gateway attach --target-tmux-session <session>
```

Detach:

```text
<chosen houmao-mgr launcher> agents gateway detach --agent-name <name>
<chosen houmao-mgr launcher> agents gateway detach --agent-id <id>
<chosen houmao-mgr launcher> agents gateway detach --target-tmux-session <session>
```

Status:

```text
<chosen houmao-mgr launcher> agents gateway status --agent-name <name>
<chosen houmao-mgr launcher> agents gateway status --agent-id <id>
<chosen houmao-mgr launcher> agents gateway status --target-tmux-session <session>
```

Background attach is explicit:

```text
<chosen houmao-mgr launcher> agents gateway attach --background --agent-name <name>
```

Pair-managed lifecycle routes:

- `POST /houmao/agents/{agent_ref}/gateway/attach`
- `POST /houmao/agents/{agent_ref}/gateway/detach`
- `GET /houmao/agents/{agent_ref}/gateway`

## Guardrails

- Do not use this action to launch or stop the managed agent process; use `houmao-agent-instance` for that.
- Do not combine `--pair-port` with `--current-session` or `--target-tmux-session`.
- Do not describe `--pair-port` as the live gateway listener port; it selects Houmao pair authority only.
- Do not assume attach succeeds just because the session is gateway-capable.
- Do not confuse detached offline status with permanent loss of gateway capability.
