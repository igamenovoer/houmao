# Prompt A Managed Agent

Use this action when the user wants one normal conversational turn for an already-running managed agent.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and prompt text from the current prompt first and recent chat context second when they were stated explicitly.
3. If the target selector or prompt text is still missing, ask the user in Markdown before proceeding.
4. Use `agents single ... prompt` or `agents self prompt` for the CLI lane, or `POST /houmao/agents/{agent_ref}/requests` for the pair-managed HTTP lane. With a detached gateway, the CLI uses its authorized route to the selected owner and checks prompt readiness there.
5. Report the prompt outcome. For a TUI handoff, say that the terminal accepted input and provider completion is unconfirmed. If the owner route is unavailable, report the failure without sending input through a different session.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> prompt --prompt "<message>"
```

When the user requests a turn-scoped model or reasoning override and the selected prompt surface supports it, add `--model <name>` and `--reasoning-level <integer>`. Codex GPT-5.6 rejects level 0. Sol and Terra support six ordered levels through `ultra`, while Luna supports five through `max`. For Kimi, use an alias from the managed native config. Positive levels index that model's effective `support_efforts` from 1 and saturate at its final entry. Level 0 requires a model that permits thinking off. The turn uses the selected alias's native effort, then restores the earlier thinking settings.

Authoritative selector alternatives:

- `--agent-id <id>`
- `--port <pair-port>`

If `--prompt` is omitted, `agents single ... prompt` and `agents self prompt` accept piped stdin.

Managed-agent HTTP prompt surfaces:

- `POST /houmao/agents/{agent_ref}/requests`

## Guardrails

- Do not redirect ordinary prompt-turn work to `agents single ... gateway send-keys` or `agents self gateway send-keys`.
- Use [gateway-queue](gateway-queue.md) when the user requests gateway-specific admission or queue semantics.
- Do not guess the target managed agent or prompt body.
- Do not describe raw TUI shaping as a normal prompt-turn workflow.
