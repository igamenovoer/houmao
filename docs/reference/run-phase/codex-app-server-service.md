# Codex App-Server Service

Select `--mode service` with Codex CLI `0.169.0`. Houmao starts a private `codex app-server --listen stdio://` child in the selected workspace and `CODEX_HOME`. It verifies the native handshake and binds one conversation thread before publishing readiness. The provider and its model come from the managed home and launch configuration. [Run Modes and Backends](backends.md).

```bash
houmao-mgr project agents launch --profile codex-lab --mode service
houmao-mgr agents single --agent-id "$agent_id" prompt --prompt 'Inspect the current workspace.'
houmao-mgr agents single --agent-id "$agent_id" state
```

## Request State

The manager, signed gateway and AG-UI use the same owner reservation. Codex's `turn/start` acknowledgment identifies the accepted native turn. The owner matches `turn/completed` against that thread and turn before reporting a final outcome. It preserves partial assistant output when the turn fails or is interrupted. If the connection disappears before that outcome, use the exact managed request to inspect the retained evidence.

The native approval policy applies to the whole service. The owner declines requests that need a human answer. Service mode exposes no browser or terminal handoff. Use the launch profile to select the model and reasoning settings. The service does not expose per-request overrides.

Managed usage comes from the native rollout's response records for the exact turn. The authenticated gateway and passive server return those records by managed request ID. The collector waits for the corresponding rollout boundary before finalizing usage.

## Detach and Exact Resume

Gateway detach leaves the native connection under the owner. `interrupt` targets the current turn on the recorded thread. Stop closes the owned process. Exact relaunch establishes a new service incarnation after verifying the saved native thread and its workspace in the private home.

```bash
houmao-mgr agents single --agent-id "$agent_id" gateway detach
houmao-mgr agents single --agent-id "$agent_id" stop
houmao-mgr agents single --agent-id "$agent_id" relaunch \
  --chat-session-mode exact --chat-session-id "$native_thread_id"
houmao-mgr agents single --agent-id "$agent_id" gateway attach --background
```

Retired app-server manifests require a fresh managed launch. The current owner proves its identity through its saved incarnation, generation, native thread, and private channel. [Gateway Access and Enrollment](../gateway/operations/access.md).
