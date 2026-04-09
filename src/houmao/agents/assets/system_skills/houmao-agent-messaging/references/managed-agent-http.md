# Managed-Agent HTTP Route Summary

Prefer the pair-managed `/houmao/agents/*` seam whenever it already satisfies the task. For ordinary prompt turns and mailbox handoff, discover live gateway capability first and prefer gateway-backed delivery when it is currently available. Use direct gateway `/v1/...` only when the lower-level route is genuinely required and the exact live `gateway.base_url` is already available from current context or supported discovery.

## Discovery

- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

## Ordinary Prompt

- `GET /houmao/agents/{agent_ref}/gateway`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/requests`

Normal prompt turns should check `/gateway` first. When a live gateway exists, prefer `/gateway/control/prompt` for gateway-backed prompt delivery. Use `/requests` when no live gateway is attached or when the task explicitly wants the transport-neutral managed-agent prompt route.

## Transport-Neutral Interrupt

- `POST /houmao/agents/{agent_ref}/requests`

Use this route family for the normal managed-agent interrupt surface across both TUI and headless transports.
For TUI-backed managed agents, ordinary interrupt means one best-effort `Escape` delivery through the resolved managed-agent control path, even when tracked TUI state currently looks idle.
For headless managed agents, ordinary interrupt targets active execution and may return explicit no-op detail when no headless work is active.
Do not switch to raw `send-keys` merely to get the normal TUI interrupt behavior.

## Explicit Gateway Queue And Direct Gateway Control

- `POST /houmao/agents/{agent_ref}/gateway/requests`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- `GET /houmao/agents/{agent_ref}/gateway/control/headless/state`
- `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`

Use `/gateway/requests` for queued gateway work. Use `/gateway/control/*` for immediate gateway-owned control behavior such as prompt control, raw key delivery, or headless next-prompt-session selection.

## Gateway-Owned TUI Inspection

- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`
- `POST /houmao/agents/{agent_ref}/gateway/tui/note-prompt`

Use these routes when you need the exact raw gateway-owned tracker surface instead of the broader managed-agent history view.

## Mailbox Discovery Handoff

- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

Resolve live bindings first. Then hand mailbox work to `houmao-agent-email-comms` for ordinary mailbox operations or `houmao-process-emails-via-gateway` for one unread-email round. This messaging skill does not restate the lower-level mailbox operation routes.

## Direct Gateway HTTP

Only use these lower-level routes when the task requires the direct gateway seam and the exact live `gateway.base_url` is already available:

- `POST {gateway.base_url}/v1/control/prompt`
- `POST {gateway.base_url}/v1/control/send-keys`
- `GET {gateway.base_url}/v1/control/headless/state`
- `POST {gateway.base_url}/v1/control/headless/next-prompt-session`

Do not guess the gateway host or port.
