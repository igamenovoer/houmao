# Reset Context Or Select A New Chat Session

Use this action only when the user wants clear-context, reset-then-send, or one-shot next-prompt chat-session control for an already-running managed agent.

## Workflow

1. Recover the target selector and the exact reset intent from the current prompt first and recent chat context second when they were stated explicitly.
2. Determine whether the managed agent is TUI-backed or headless from current context or a fresh discovery step.
3. Prefer the managed-agent HTTP seam first:
   - `POST /houmao/agents/{agent_ref}/gateway/control/prompt` for immediate prompt control
   - `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` for a headless one-shot next-prompt override
4. For TUI-backed reset-then-send behavior, use prompt control with `chat_session.mode = "new"`.
5. For headless reset-then-send behavior, use prompt control with `chat_session.mode = "new"`.
6. For headless "prepare the next prompt for a fresh session but do not send it yet" behavior, use `next-prompt-session`.
7. Use direct gateway `/v1/control/prompt` or `/v1/control/headless/next-prompt-session` only when the exact live `gateway.base_url` is already available from current context or supported discovery and the task genuinely needs the lower-level gateway route.
8. State clearly when the requested reset flow cannot stay entirely on the current `houmao-mgr` surface because there is no first-class CLI flag for it yet.
9. Report the chosen HTTP route and whether the request cleared context immediately or only prepared the next headless prompt session.

## Current Supported Routes

Managed-agent HTTP:

- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session`

Direct gateway HTTP when the exact live `gateway.base_url` is already known:

- `POST {gateway.base_url}/v1/control/prompt`
- `POST {gateway.base_url}/v1/control/headless/next-prompt-session`

## Guardrails

- Do not invent a nonexistent `houmao-mgr` reset-context flag.
- Do not guess a direct gateway host or port.
- Do not misdescribe queued gateway prompt submission as reset-context control.
- Do not claim that TUI-backed reset-context currently has a no-send CLI shortcut; the current supported path is reset-then-send prompt control with `chat_session.mode = "new"`.
- Do not use direct gateway HTTP when the managed-agent `/houmao/agents/*` route already satisfies the task.
