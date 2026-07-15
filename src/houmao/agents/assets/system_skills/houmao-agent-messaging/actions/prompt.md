# Prompt A Managed Agent

Use this action only when the user wants one normal conversational turn for an already-running managed agent and expects ordinary prompt-turn behavior, with live gateway delivery preferred when the target currently has a gateway.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and prompt text from the current prompt first and recent chat context second when they were stated explicitly.
3. If the target selector or prompt text is still missing, ask the user in Markdown before proceeding.
4. When the current context does not already confirm whether the target has a live gateway, run `agents single ... gateway status` first.
5. If a live gateway exists, prefer the gateway-backed prompt surface that matches the current lane:
   - use `agents single ... gateway prompt --admission-policy ready-only` for the selected-agent CLI lane
   - use `agents self gateway prompt --admission-policy ready-only` for the current-session CLI lane
   - use `POST /houmao/agents/{agent_ref}/gateway/control/prompt` with `schema_version=2` and `admission_policy=ready_only` for pair-managed HTTP prompt delivery
6. If no live gateway exists, use `agents single ... prompt` or `agents self prompt` for the CLI lane, or `POST /houmao/agents/{agent_ref}/requests` for the pair-managed HTTP lane.
7. Report the prompt outcome and call out whether it used the live gateway-backed lane or the fallback managed-agent lane.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway status
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway prompt --admission-policy ready-only --prompt "<message>"
<chosen houmao-mgr launcher> agents single --agent-name <name> prompt --prompt "<message>"
```

When the user requests a turn-scoped model or reasoning override and the selected prompt surface supports it, add `--model <name>` and `--reasoning-level <integer>`. Codex GPT-5.6 rejects level 0; Sol and Terra support six ordered levels through `ultra`, while Luna supports five through `max`. Kimi config-backed models derive their native effort order from the selected alias's effective `support_efforts`; Kimi env-model credentials reject normalized reasoning overrides because they expose no ordered catalog.

Authoritative selector alternatives:

- `--agent-id <id>`
- `--port <pair-port>`

If `--prompt` is omitted, `agents single ... prompt` and `agents self prompt` accept piped stdin.

Managed-agent HTTP prompt surfaces:

- `GET /houmao/agents/{agent_ref}/gateway`
- `POST /houmao/agents/{agent_ref}/gateway/control/prompt`
- `POST /houmao/agents/{agent_ref}/requests`

## Guardrails

- Do not redirect ordinary prompt-turn work to `agents single ... gateway send-keys` or `agents self gateway send-keys`.
- Do not assume a gateway is attached without checking live status when the current context does not already confirm it.
- Do not fall back to `agents single ... prompt`, `agents self prompt`, or `POST /houmao/agents/{agent_ref}/requests` before checking whether the target currently has a live gateway.
- Do not guess the target managed agent or prompt body.
- Do not describe raw TUI shaping as a normal prompt-turn workflow.
- Do not select `if-no-pending` or `always` for an ordinary prompt unless the user explicitly asks for their busy-TUI semantics.
- Do not bypass the managed-agent seam with direct gateway `/v1/control/prompt` when `POST /houmao/agents/{agent_ref}/gateway/control/prompt`, scoped `agents ... gateway prompt`, scoped `agents ... prompt`, or `POST /houmao/agents/{agent_ref}/requests` already satisfies the task.
