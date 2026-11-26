# Discover Managed and External Agent State

## Workflow

1. **Resolve the target selector** from explicit prompt or recent context; if omitted or ambiguous, run `houmao-mgr agents global list` (and `houmao-mgr agents external list` when remote communication-only imports may apply) or ask before proceeding.
2. **Read summary posture first** via `houmao-mgr agents single --agent-id|--agent-name ... state` (or `agents self state`, `agents external get --name <alias>`, or `GET /houmao/agents/{agent_ref}/managed-state`), noting liveness, run mode (`headless`, `service`, `tui`, `web`), `execution_binding` (`--executor` context), gateway `admin_mode`/policy/`default_group` summary, `manifest_path`, and `session_root`.
3. **Query transport-specific detail** when needed:
   - Pair-managed detail: `GET /houmao/agents/{agent_ref}/managed-state/detail` or `/state/detail`, plus `agents single ... gateway status` (`GET /houmao/agents/{agent_ref}/gateway`).
   - `service` mode: `GET {gateway.base_url}/v1/control/service/state` and `GET {gateway.base_url}/v1/control/service/requests/{request_id}` (or pair-managed `/houmao/agents/{agent_ref}/gateway/control/service/*`).
   - `web` mode: `GET {gateway.base_url}/v1/control/web/state` and `GET {gateway.base_url}/v1/control/web/history` (or pair-managed `/houmao/agents/{agent_ref}/gateway/control/web/*`).
4. **Report concise facts** (identity, run mode, `execution_binding`, gateway/policy posture, and artifact pointers) for the next step.

If the request does not map cleanly to these steps, use the native planning tool to build a bounded read-only discovery plan from [../SKILL-MAIN.md](../SKILL-MAIN.md) and the user request, then execute the plan.

## Command Shapes

```bash
<chosen houmao-mgr launcher> agents global list
<chosen houmao-mgr launcher> agents external list
<chosen houmao-mgr launcher> agents external get --name <alias>
<chosen houmao-mgr launcher> agents single --agent-id <id> state [--port <pair-port>]
<chosen houmao-mgr launcher> agents single --agent-id <id> gateway status [--pair-port <pair-port>]
<chosen houmao-mgr launcher> agents self state
```

## Guardrails

- DO NOT guess an ambiguous target or skip `state` / `managed-state` before inspecting local tmux or filesystem paths.
- DO NOT treat `/history` as a substitute for transport-specific `managed-state/detail`, `service/state`, or `web/state`, or reuse stale gateway coordinates across turns.
