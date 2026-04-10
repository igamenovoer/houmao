# Inspect Logs And Durable Turn Evidence

Use this action when the user wants logs, turn traces, or append-only runtime evidence for one managed agent.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and, for headless turns, the specific `turn_id` from the current prompt first and recent chat context second when they were stated explicitly.
3. If a required target or `turn_id` is still missing, ask the user in Markdown before proceeding.
4. For headless agents, prefer the managed turn surfaces first:
   - `agents turn status` for one persisted turn status payload
   - `agents turn events` for canonical semantic event replay
   - `agents turn stdout` and `agents turn stderr` for raw durable artifacts
5. For gateway-capable sessions, inspect `gateway/logs/gateway.log` when the task is about gateway lifecycle, queue execution, or notifier polling logs.
6. Inspect `gateway/events.jsonl` only as append-only event evidence, not as the source of truth for durable queue or manifest state.
7. When the user wants the overall current posture rather than one specific turn, return to `actions/discover.md` and `actions/screen.md` first before diving into raw logs.

## Command Shapes

Headless turn inspection:

```text
<chosen houmao-mgr launcher> agents turn status --agent-name <name> <turn-id>
<chosen houmao-mgr launcher> agents turn events --agent-name <name> <turn-id>
<chosen houmao-mgr launcher> agents turn stdout --agent-name <name> <turn-id>
<chosen houmao-mgr launcher> agents turn stderr --agent-name <name> <turn-id>
```

Managed-agent HTTP headless routes:

- `GET /houmao/agents/{agent_ref}/turns/{turn_id}`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr`

Runtime log artifacts:

- `<session-root>/gateway/logs/gateway.log`
- `<session-root>/gateway/events.jsonl`
- `<session-root>/<manifest-stem>.turn-artifacts/<turn-id>/stdout.jsonl`
- `<session-root>/<manifest-stem>.turn-artifacts/<turn-id>/stderr.log`

## Guardrails

- Do not treat `/history` as the durable headless turn store.
- Do not claim that `gateway.log` or `events.jsonl` is the authoritative source of truth for manifest-backed or queue-backed state.
- Do not infer current runtime posture primarily from raw logs when managed-agent summary or detail surfaces already answer the question.
- Do not guess a `turn_id` from incomplete context.
