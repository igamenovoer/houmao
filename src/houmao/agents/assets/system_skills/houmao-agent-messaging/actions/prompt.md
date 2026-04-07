# Prompt A Managed Agent

Use this action only when the user wants one normal conversational turn for an already-running managed agent and expects ordinary prompt-turn behavior, with live gateway delivery preferred when the target currently has a gateway.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the target selector and prompt text from the current prompt first and recent chat context second when they were stated explicitly.
3. If the target selector or prompt text is still missing, ask the user in Markdown before proceeding.
4. When the current context does not already confirm whether the target has a live gateway, run `agents gateway status` first.
5. If a live gateway exists, prefer the gateway-backed prompt surface that matches the current lane:
   - use `agents gateway prompt` for the CLI lane
   - use `POST /houmao/agents/{agent_ref}/gateway/control/prompt` for pair-managed HTTP prompt delivery
6. If no live gateway exists, use `agents prompt` for the CLI lane or `POST /houmao/agents/{agent_ref}/requests` for the pair-managed HTTP lane.
7. Report the prompt outcome and call out whether it used the live gateway-backed lane or the fallback managed-agent lane.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> agents gateway status --agent-name <name>
<resolved houmao-mgr launcher> agents gateway prompt --agent-name <name> --prompt "<message>"
<resolved houmao-mgr launcher> agents prompt --agent-name <name> --prompt "<message>"
```

Authoritative selector alternatives:

- `--agent-id <id>`
- `--port <pair-port>`

If `--prompt` is omitted, `agents prompt` accepts piped stdin.

Managed-agent HTTP prompt surfaces:

- `GET /houmao/agents/{agent_ref}/gateway`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/requests`

## Guardrails

- Do not redirect ordinary prompt-turn work to `agents gateway send-keys`.
- Do not assume a gateway is attached without checking live status when the current context does not already confirm it.
- Do not fall back to `agents prompt` or `POST /houmao/agents/{agent_ref}/requests` before checking whether the target currently has a live gateway.
- Do not guess the target managed agent or prompt body.
- Do not describe raw TUI shaping as a normal prompt-turn workflow.
- Do not bypass the managed-agent seam with direct gateway `/v1/control/prompt` when `POST /houmao/agents/{agent_ref}/gateway/control/prompt`, `agents gateway prompt`, `agents prompt`, or `POST /houmao/agents/{agent_ref}/requests` already satisfies the task.
