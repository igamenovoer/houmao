# Kimi Code ACP Service

Select `--mode service` with Kimi Code 2.6.0 or later. Houmao starts `kimi acp` in the selected workspace and private Kimi home. The supervisor verifies the peer version and ACP protocol, records its capabilities, and keeps one native session open across prompts. The native home supplies the role through `SYSTEM.md` and the selected model and authentication configuration. [Run Modes and Backends](backends.md)

```bash
houmao-mgr project agents launch --profile kimi-lab --mode service
houmao-mgr agents single --agent-id "$agent_id" prompt --prompt 'Inspect the current workspace.'
houmao-mgr agents single --agent-id "$agent_id" state
```

## Control and Permissions

The manager, authenticated gateway, and AG-UI use the same prompt reservation. The service reports the bound native session, its current incarnation, readiness, and an active request when it can verify one. Gateway request state distinguishes accepted work, native transport handoff, and a settled turn. The stdio endpoint stays private.

Houmao sends ordinary text over ACP. Choose the model and any explicit `tool_params.permission_mode` (`auto`, `yolo`, or `manual`) before starting or relaunching. Unattended launch fills an omitted mode with `auto`. With `as_is`, an omitted field uses Kimi's native mode. On fresh and exact resumed startup, the owner verifies the selected ACP mode. Kimi calls `manual` permission `default` in ACP. If Kimi asks for a human approval, a plan decision, or a question answer, the owner declines it. The owner advertises an empty client capability set, which keeps filesystem and terminal work with the native process.

## Detach and Exact Continuation

Gateway detach leaves the service and any active request running. Interrupt targets the current request through the exact owner. Stop closes the owned process. Relaunch creates a new service incarnation and checks the saved Kimi session in the current private home and workspace before resuming it.

```bash
houmao-mgr agents single --agent-id "$agent_id" gateway detach
houmao-mgr agents single --agent-id "$agent_id" stop
houmao-mgr agents single --agent-id "$agent_id" relaunch \
  --chat-session-mode exact --chat-session-id "$native_session_id"
houmao-mgr agents single --agent-id "$agent_id" gateway attach --background
```

The owner uses ACP `session/resume` when the native build advertises it. Any negotiated history replay happens during binding. Request settlement and qualified per-turn usage come from the exact native journal interval. ACP context occupancy, earlier history, and uncorrelated updates stay outside current request output and usage. If transport loss leaves the outcome uncertain, inspect the original request before attempting another input. [Usage Records](usage-records.md)
