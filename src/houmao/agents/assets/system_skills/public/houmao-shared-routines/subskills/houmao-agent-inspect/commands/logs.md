# Inspect Turn Usage, Mode Logs, and Gateway Evidence

## Workflow

1. **Resolve the target agent** (and explicit `turn_id` or `request_id` when inspecting a specific turn/request) before querying logs.
2. **Select the authoritative read-only evidence surface** for the question:
   - **Durable turn token/cost usage**: query `GET {gateway.base_url}/v1/usage` (supports pagination filters) or pair-managed `GET /houmao/agents/{agent_ref}/usage`, or inspect per-turn `usage-start.json` / `usage-final.json` and `<session-root>/usage/records.sqlite3` when offline.
   - **Headless turns**: run `houmao-mgr agents single ... turn {status|events|stdout|stderr} <turn-id>` (or `GET /houmao/agents/{agent_ref}/turns/{turn_id}[/events|/artifacts/stdout|/artifacts/stderr]`).
   - **`service` and `web` sessions**: query `GET {gateway.base_url}/v1/control/service/requests/{request_id}` for structured service request traces or `GET {gateway.base_url}/v1/control/web/history` for Web session history (or their `/houmao/agents/{agent_ref}/gateway/control/*` equivalents).
   - **Gateway operational logs**: read `<session-root>/gateway/logs/gateway.log` and append-only `<session-root>/gateway/events.jsonl` as diagnostic logs, never as authoritative manifest or queue state.
3. **Return concise evidence** and step back to [discover.md](discover.md) or [screen.md](screen.md) when overall liveness rather than a specific turn or log is requested.

If the request does not map cleanly to these steps, use the native planning tool to build a bounded read-only log/usage plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the user request, then execute the plan.

## Command and HTTP Shapes

```bash
<chosen houmao-mgr launcher> agents single --agent-name <name> turn status <turn-id>
<chosen houmao-mgr launcher> agents single --agent-name <name> turn events <turn-id>
<chosen houmao-mgr launcher> agents single --agent-name <name> turn stdout <turn-id>
<chosen houmao-mgr launcher> agents single --agent-name <name> turn stderr <turn-id>
```

- Usage HTTP routes: `GET {gateway.base_url}/v1/usage`, `GET /houmao/agents/{agent_ref}/usage`
- Service/Web HTTP routes: `GET {gateway.base_url}/v1/control/service/requests/{request_id}`, `GET {gateway.base_url}/v1/control/web/history`
- Session log files: `<session-root>/gateway/logs/gateway.log`, `<session-root>/gateway/events.jsonl`, `<session-root>/<manifest-stem>.turn-artifacts/<turn-id>/{stdout.jsonl,stderr.log,usage-start.json,usage-final.json}`

## Guardrails

- DO NOT guess a missing `turn_id` or `request_id`, or treat `/history`, `gateway.log`, or `events.jsonl` as the durable headless turn or manifest store.
