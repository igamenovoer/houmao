# Use Gateway-Only Services

Use this action when the task specifically needs the live gateway's own control, queueing, raw-input, TUI inspection, or headless-session surfaces instead of the broader transport-neutral managed-agent path.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and the exact gateway service the user wants from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target, prompt body, sequence, or direct-gateway endpoint, ask the user in Markdown before proceeding.
4. Run `agents gateway status` first unless current context already proves that a live gateway is attached.
5. Use `agents gateway prompt` or `POST /houmao/agents/{agent_ref}/gateway/control/prompt` for immediate gateway-owned prompt control.
6. Use `agents gateway interrupt` or `POST /houmao/agents/{agent_ref}/gateway/requests` when the task explicitly wants gateway-mediated interrupt handling.
7. Use `agents gateway send-keys` or `POST /houmao/agents/{agent_ref}/gateway/control/send-keys` for exact raw key delivery.
8. Use `agents gateway tui state|history|watch|note-prompt` or the matching pair-managed routes for raw gateway-owned tracker inspection.
9. Use direct `{gateway.base_url}/v1/...` routes only when the task genuinely needs the lower-level gateway seam and the exact live base URL is already available from current context or supported discovery.
10. When the attached agent needs to communicate with other agents through the shared mailbox facade, use `houmao-mgr agents mail resolve-live` to obtain the exact current `gateway.base_url`, then hand off the exact `/v1/mail/*` contract to `houmao-agent-email-comms`.

## Command Shapes

Gateway-mediated CLI control:

```text
<chosen houmao-mgr launcher> agents gateway prompt --agent-name <name> --prompt "<message>"
<chosen houmao-mgr launcher> agents gateway interrupt --agent-name <name>
<chosen houmao-mgr launcher> agents gateway send-keys --agent-name <name> --sequence "<[Escape]>"
<chosen houmao-mgr launcher> agents gateway tui state --agent-name <name>
<chosen houmao-mgr launcher> agents gateway tui history --agent-name <name>
<chosen houmao-mgr launcher> agents gateway tui watch --agent-name <name>
<chosen houmao-mgr launcher> agents gateway tui note-prompt --agent-name <name> --prompt "<note>"
```

Pair-managed gateway routes:

- `POST /houmao/agents/{agent_ref}/gateway/requests`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`
- `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`
- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`

Direct live gateway routes:

- `POST {gateway.base_url}/v1/requests`
- `POST {gateway.base_url}/v1/control/prompt`
- `POST {gateway.base_url}/v1/control/send-keys`
- `GET {gateway.base_url}/v1/control/headless/state`
- `POST {gateway.base_url}/v1/control/headless/next-prompt-session`
- `GET {gateway.base_url}/v1/control/tui/state`
- `GET {gateway.base_url}/v1/control/tui/history`
- `POST {gateway.base_url}/v1/control/tui/note-prompt`

## Guardrails

- Do not silently replace explicit gateway work with `houmao-mgr agents prompt` or the transport-neutral `/houmao/agents/{agent_ref}/requests` surface.
- Do not use raw `send-keys` as a substitute for ordinary prompt-turn work.
- Do not claim that `tui note-prompt` submits work to the agent.
- Do not guess `{gateway.base_url}` when the exact live gateway endpoint is not already available.
- Do not restate the full shared mailbox route contract here; use `houmao-agent-email-comms` after discovery hands you the exact live base URL.
