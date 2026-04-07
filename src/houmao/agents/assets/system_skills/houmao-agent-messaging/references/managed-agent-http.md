# Managed-Agent HTTP Route Summary

Prefer the pair-managed `/houmao/agents/*` seam whenever it already satisfies the task. For ordinary prompt turns and mailbox follow-up, discover live gateway capability first and prefer gateway-backed delivery when it is currently available. Use direct gateway `/v1/...` only when the lower-level route is genuinely required and the exact live `gateway.base_url` is already available from current context or supported discovery.

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

## Mailbox Follow-Up

- `GET /houmao/agents/{agent_ref}/mail/resolve-live`
- `GET /houmao/agents/{agent_ref}/mail/status`
- `POST /houmao/agents/{agent_ref}/mail/check`
- `POST /houmao/agents/{agent_ref}/mail/send`
- `POST /houmao/agents/{agent_ref}/mail/reply`
- `POST /houmao/agents/{agent_ref}/mail/state`

Resolve live bindings first. When `mail/resolve-live` returns a live `gateway.base_url`, prefer the shared gateway mailbox facade for outgoing or other shared mailbox operations. Use the `/houmao/agents/{agent_ref}/mail/*` routes as the transport-neutral fallback when no live gateway mailbox facade is available or the task explicitly stays on the managed-agent seam.

## Direct Gateway HTTP

Only use these lower-level routes when the task requires the direct gateway seam and the exact live `gateway.base_url` is already available:

- `POST {gateway.base_url}/v1/control/prompt`
- `POST {gateway.base_url}/v1/control/send-keys`
- `GET {gateway.base_url}/v1/control/headless/state`
- `POST {gateway.base_url}/v1/control/headless/next-prompt-session`
- `POST {gateway.base_url}/v1/mail/*`

Do not guess the gateway host or port.
