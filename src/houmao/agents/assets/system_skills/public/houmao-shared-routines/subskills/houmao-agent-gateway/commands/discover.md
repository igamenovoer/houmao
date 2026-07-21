# Discover The Current Gateway

Use this action when the caller needs to find the current managed session, confirm whether a live gateway exists, or choose the correct direct gateway endpoint from inside or outside the attached session.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target mode from the current prompt first and recent chat context second when it was stated explicitly:
   - current managed tmux session
   - explicit managed-agent selector
   - pair-managed `agent_ref`
3. If the target is still ambiguous, ask the user in Markdown before proceeding.
4. For current-session targeting, use manifest-first discovery:
   - `HOUMAO_MANIFEST_PATH` is the preferred current-session locator
   - `HOUMAO_AGENT_ID` plus shared-registry lookup is the fallback when the manifest pointer is missing or stale
5. Run `agents single ... gateway status` for an explicit selected agent, run `agents self gateway status` for the current managed session, or use `GET /houmao/agents/{agent_ref}/gateway` to confirm whether a live gateway is attached right now.
6. When the task needs exact shared mailbox gateway coordinates, run `agents self mail resolve-live`, run `agents single ... mail resolve-live`, or use `GET /houmao/agents/{agent_ref}/mail/resolve-live` and read `gateway.base_url`.
7. Use live env vars `HOUMAO_AGENT_GATEWAY_HOST` and `HOUMAO_AGENT_GATEWAY_PORT` only when the task genuinely needs direct gateway `/v1/...` HTTP and the current session already publishes valid live bindings.
8. If a prompt or notifier already provided the exact `gateway.base_url`, use that value directly instead of rediscovering it.
9. Report only the facts the next action needs: target identity, whether the gateway is live, the exact `gateway.base_url` when it is supported and known, and whether the task should stay on the managed-agent seam or may use direct gateway HTTP.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shapes

Managed-agent discovery:

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> gateway status
<chosen houmao-mgr launcher> agents self gateway status
<chosen houmao-mgr launcher> agents self mail resolve-live
```

Pair-managed discovery:

- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

Direct current-session gateway base URL from live env when already attached:

```text
http://$HOUMAO_AGENT_GATEWAY_HOST:$HOUMAO_AGENT_GATEWAY_PORT
```

## Guardrails

- Do not teach `HOUMAO_GATEWAY_ATTACH_PATH` or `HOUMAO_GATEWAY_ROOT` as supported discovery.
- Do not guess a localhost listener port from tmux names, logs, or unrelated processes.
- Do not scrape live gateway env for shared mailbox work when `agents self mail resolve-live` already provides the exact supported `gateway.base_url`.
- Do not assume that a running managed agent currently has a live gateway attached.
- Do not keep using stale gateway coordinates across turns when the task depends on the current live gateway.
