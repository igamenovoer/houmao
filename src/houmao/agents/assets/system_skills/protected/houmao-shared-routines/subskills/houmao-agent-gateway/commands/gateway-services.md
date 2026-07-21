# Use Gateway-Only Services

Use this action when the task specifically needs the live gateway's own control, queueing, raw-input, TUI inspection, or headless-session surfaces instead of the broader transport-neutral managed-agent path. If the request is generic managed-agent inspection rather than a gateway-owned service, use `<public-entrypoint>->houmao-shared-routines->agent-inspect` instead.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and the exact gateway service the user wants from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target, prompt body, sequence, or direct-gateway endpoint, ask the user in Markdown before proceeding.
4. Run `agents single ... gateway status` or `agents self gateway status` first unless current context already proves that a live gateway is attached.
5. Run the matching direct gateway command for CLI prompt, interrupt, send-keys, or TUI work.
6. Use the matching pair-managed routes when the task is already operating through pair-managed HTTP.
7. Use direct `{gateway.base_url}/v1/...` routes only when the task genuinely needs the lower-level gateway seam and the exact live base URL is already available from current context or supported discovery.
8. When the attached agent needs to communicate with other agents through the shared mailbox facade, run `agents self mail resolve-live` to obtain the exact current `gateway.base_url`, then hand off the exact `/v1/mail/*` contract to `<public-entrypoint>->houmao-shared-routines->agent-email-comms`.

## Command Shapes

Run direct scoped gateway-service commands:

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway prompt --prompt <text>
<chosen houmao-mgr launcher> agents self gateway prompt --prompt <text>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway send-keys --sequence <keys>
<chosen houmao-mgr launcher> agents self gateway tui state
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

- Do not silently replace explicit gateway work with `houmao-mgr agents single ... prompt`, `houmao-mgr agents self prompt`, or the transport-neutral `/houmao/agents/{agent_ref}/requests` surface.
- Do not use raw `send-keys` as a substitute for ordinary prompt-turn work.
- Do not claim that `tui note-prompt` submits work to the agent.
- Do not guess `{gateway.base_url}` when the exact live gateway endpoint is not already available.
- Do not restate the full shared mailbox route contract here; use `<public-entrypoint>->houmao-shared-routines->agent-email-comms` after discovery hands you the exact live base URL.
- Do not guess prompt text, key sequences, or live gateway endpoints.
