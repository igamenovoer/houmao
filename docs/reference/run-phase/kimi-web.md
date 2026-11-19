# Kimi Web

Select `--mode web` with Kimi Code `2.6.0`. Houmao supervises `kimi web --no-open` in the private Kimi home and binds one conversation in the selected workspace. The browser and authenticated gateway address that same conversation through Kimi's native API. [Run Modes and Backends](backends.md).

```bash
houmao-mgr project agents launch --profile kimi-lab --mode web
houmao-mgr agents single --agent-id "$agent_id" open-browser
houmao-mgr agents single --agent-id "$agent_id" prompt --prompt 'Inspect the workspace.'
```

The browser handoff contains a clean loopback origin and native session ID. Owner-local browser opening uses the credential privately. In a routed context, use the verified origin and execution placement to reach the corresponding loopback host. Keep the native credential in the owner context.

## Sending While the Browser Is Active

The manager and gateway share one managed prompt reservation. The owner checks Kimi's live active prompt and pending queue immediately before sending. If it sees active or pending work, it refuses the ordinary prompt before sending. The browser can still start a turn after the check. In that case, Houmao reports the same prompt as queued if Kimi queues it. A lost response is reconciled using the original prompt identity.

Select the model at launch. Per-request model and permission changes are unavailable through ordinary Kimi Web delivery. Kimi can change session settings before inserting a prompt.

## Host Lifetime

Gateway detach leaves the owned Kimi Web process and browser session open. The next gateway verifies the same host and exact native conversation. Stop closes the owned process. Set `--chat-session-mode exact --chat-session-id "$native_session_id"` on an explicit relaunch to preserve the conversation.
