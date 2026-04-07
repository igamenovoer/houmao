# Prompt A Managed Agent

Use this action only when the user wants one normal conversational turn for an already-running managed agent and expects ordinary prompt-turn behavior.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the target selector and prompt text from the current prompt first and recent chat context second when they were stated explicitly.
3. If the target selector or prompt text is still missing, ask the user in Markdown before proceeding.
4. Use `agents prompt` for the default CLI path.
5. If the caller is already using the pair-managed HTTP API, use `POST /houmao/agents/{agent_ref}/requests` through the managed-agent prompt surface instead of jumping to direct gateway HTTP.
6. Report the prompt-turn outcome returned by the selected managed-agent surface.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> agents prompt --agent-name <name> --prompt "<message>"
```

Authoritative selector alternatives:

- `--agent-id <id>`
- `--port <pair-port>`

If `--prompt` is omitted, `agents prompt` accepts piped stdin.

## Guardrails

- Do not redirect ordinary prompt-turn work to `agents gateway prompt` unless the user explicitly wants queue semantics.
- Do not redirect ordinary prompt-turn work to `agents gateway send-keys`.
- Do not guess the target managed agent or prompt body.
- Do not describe raw TUI shaping as a normal prompt-turn workflow.
- Do not bypass the managed-agent seam with direct gateway `/v1/control/prompt` when `agents prompt` or `/houmao/agents/{agent_ref}/requests` already satisfies the task.
