# Manage Live Gateway Lifecycle

Use this action when the gateway itself needs to be attached, detached, or inspected from outside the attached agent session.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and requested lifecycle action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target or clear action, ask the user in Markdown before proceeding.
4. Use `attach` to start or reuse the live gateway sidecar for an already-running managed agent. For tmux-backed managed sessions, foreground same-session auxiliary-window attach is the default; do not add background posture unless the user explicitly asks for background or detached gateway execution.
5. Use `detach` to stop the live gateway while leaving the session gateway-capable for later reattach.
6. Use `status` when the caller first needs to confirm whether the session is gateway-capable, not attached, or currently live.
7. Render `agents.single.gateway.attach|detach|status` for selected-agent CLI lifecycle work, or `agents.self.gateway.attach|detach|status` for current-session CLI lifecycle work.
8. If the caller is already operating through the pair-managed HTTP API, use the matching `/houmao/agents/{agent_ref}/gateway` lifecycle routes instead of direct `/v1/...`.
9. Report whether the gateway is attached now, the current `gateway_health`, the live host and port when present, and any foreground execution metadata returned by status.

## Command Shapes

Use the CLI-owned lifecycle templates, then run the rendered `argv`:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id agents.single.gateway.attach --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id agents.single.gateway.detach --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id agents.single.gateway.status --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id agents.self.gateway.status --intent '<json>'
```

For tmux-backed managed sessions, these attach forms use foreground same-session auxiliary-window execution when supported. The managed-agent surface remains tmux window `0`; the live gateway sidecar uses a non-zero auxiliary tmux window. Treat returned `execution_mode` and `gateway_tmux_window_index` from status or attach output as authoritative; do not infer topology from tmux window names or ordering.

Use `--gateway-tui-watch-poll-interval-seconds`, `--gateway-tui-stability-threshold-seconds`, `--gateway-tui-completion-stability-seconds`, `--gateway-tui-unknown-to-stalled-timeout-seconds`, `--gateway-tui-stale-active-recovery-seconds`, or `--gateway-tui-final-stable-active-recovery-seconds` only when the user explicitly asks to tune gateway TUI tracking timing or safeguard timing. Values are positive seconds and affect the attached gateway sidecar, not the managed agent's foreground/background posture.

Pair-managed lifecycle routes:

- `POST /houmao/agents/{agent_ref}/gateway/attach`
- `POST /houmao/agents/{agent_ref}/gateway/detach`
- `GET /houmao/agents/{agent_ref}/gateway`

## Guardrails

- Do not use this action to launch or stop the managed agent process; use `houmao-agent-instance` for that.
- Do not use `--pair-port` on `agents self gateway ...`; it belongs only to selected-agent pair-authority targeting.
- Do not describe `--pair-port` as the live gateway listener port; it selects Houmao pair authority only.
- Do not assume attach succeeds just because the session is gateway-capable.
- Do not confuse detached offline status with permanent loss of gateway capability.
- Do not choose `--background` by default; background gateway execution is an explicit user override, not the normal attach posture.
- Do not add `--gateway-tui-*` timing overrides unless the user asked for custom TUI tracking or safeguard timings.
- Do not hand-author supported lifecycle commands from Markdown skeletons.
