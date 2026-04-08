# Schedule Gateway Wakeups

Use this action when the attached agent needs a reminder about unfinished work and a live gateway is already attached.

## Workflow

1. Confirm that the task really wants a gateway-owned reminder rather than a durable external scheduler.
2. Use the `houmao-mgr` launcher already chosen by the top-level skill when managed-agent discovery is still needed.
3. Recover the exact prompt text plus one timing mode from the current prompt first and recent chat context second when they were stated explicitly:
   - `after_seconds`
   - `deliver_at_utc`
4. Recover whether the wakeup is `one_off` or `repeat`.
5. If the task needs the direct live gateway endpoint first, use `actions/discover.md`.
6. Create the wakeup through direct live `{gateway.base_url}/v1/wakeups`.
7. Use `GET /v1/wakeups` or `GET /v1/wakeups/{job_id}` to inspect current live wakeup state, and `DELETE /v1/wakeups/{job_id}` to cancel one job.
8. Report the created or updated wakeup job id, next due time, and whether the reminder is one-off or repeating.

## Direct Gateway Routes

- `POST {gateway.base_url}/v1/wakeups`
- `GET {gateway.base_url}/v1/wakeups`
- `GET {gateway.base_url}/v1/wakeups/{job_id}`
- `DELETE {gateway.base_url}/v1/wakeups/{job_id}`

Representative create payload:

```json
{
  "schema_version": 1,
  "mode": "repeat",
  "prompt": "Resume the partially finished refactor.",
  "after_seconds": 300,
  "interval_seconds": 300
}
```

## Guardrails

- Do not claim that wakeups survive gateway stop or restart; they are process-local in-memory state.
- Do not invent a `houmao-mgr agents gateway wakeups ...` wrapper; the supported public wakeup surface is direct live gateway HTTP only.
- Do not invent `/houmao/agents/{agent_ref}/gateway/wakeups` pair-managed routes; they do not exist.
- Do not create a repeating wakeup without `interval_seconds`.
- Do not set both `after_seconds` and `deliver_at_utc` in the same request.
- Do not describe wakeups as extending the durable public `POST /v1/requests` kinds.
