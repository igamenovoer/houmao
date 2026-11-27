# DSH ACP Service

Select `--mode service` with DSH 0.2.2-rc.3 or later. Houmao starts a private supervisor in the saved execution context. The supervisor starts `dsh --profile acp`, negotiates ACP, and binds a native session in the recorded workspace. It keeps the reader and writer open across prompts. [Run Modes and Backends](backends.md)

```bash
houmao-mgr project agents launch --profile dsh-lab --mode service
houmao-mgr agents single --agent-id "$agent_id" prompt --prompt 'Inspect the current workspace.'
houmao-mgr agents single --agent-id "$agent_id" state
```

The manager and authenticated gateway use the same current owner. The gateway enforces its enrolled access policy and reports request acceptance separately from native handoff. Service state reports owner liveness, connection readiness, the bound native session, and any attributable active request. Raw terminal input and human handoff are unavailable for this stdio service. Native pipes, socket authority, and provider credentials stay in the owner's execution context. [Gateway access and enrollment](../gateway/operations/access.md).

## Lifecycle

Gateway detach leaves the native connection and any active request with the supervisor. An interrupt targets the active operation and waits for bounded native settlement. Stop closes the native session and reaps the owned service. An explicit exact relaunch creates a new service incarnation using the saved conversation in the same workspace and private home.

```bash
houmao-mgr agents single --agent-id "$agent_id" gateway detach
houmao-mgr agents single --agent-id "$agent_id" state
houmao-mgr agents single --agent-id "$agent_id" stop
houmao-mgr agents single --agent-id "$agent_id" relaunch \
  --chat-session-mode exact --chat-session-id "$native_session_id"
houmao-mgr agents single --agent-id "$agent_id" gateway attach --background
```

If the native child or service owner disappears, state exposes unavailable or uncertain work. An explicit lifecycle command must establish a new owner. Resumption checks the selected session before accepting a prompt.

## Native Home

The service reads role text, provider configuration, and the configured skill loader when it starts. It binds qualified typed MCP declarations when it creates or resumes the ACP session. `refresh --check` reports these boundaries for the current service. Apply edited startup resources with an explicit relaunch. Use the exact session option when preserving the conversation. [Native home and refresh](native-refresh.md).

Unattended launch requires `danger-full-access` and `never`. Use `as_is` to select a custom sandbox or approval policy. Omitted `as_is` fields use the native baseline. The native session binding verifies the selected permission preset on startup and exact relaunch. [DSH permission fields](dsh-headless.md#startup-permissions-and-prompt-provenance)

A supported request-scoped model or reasoning override is temporary. The owner verifies that it restored the prior setting before admitting conflicting work.
