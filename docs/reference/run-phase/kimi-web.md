# Kimi Web

Select `--mode web` with Kimi Code `2.6.0`. Houmao supervises `kimi web --no-open` in the private Kimi home and binds one conversation in the selected workspace. The browser and authenticated gateway address that same conversation through Kimi's native API. [Run Modes and Backends](backends.md).

```bash
houmao-mgr project agents launch --profile kimi-lab --mode web
houmao-mgr agents single --agent-id "$agent_id" open-browser
houmao-mgr agents single --agent-id "$agent_id" prompt --prompt 'Inspect the workspace.'
```

The published browser surface contains a clean loopback origin and native session ID. `open-browser` opens the native UI from the owner execution context. For gateway entry, open the owning gateway's `/v1/web/enter` page or request a signed `gateway web-entry` link. [Gateway Access](../gateway/operations/access.md).

The gateway verifies the Kimi listener, host, and exact conversation before handing off to `/sessions/<id>` with Kimi's private token fragment. The qualified Kimi Code `2.6.0` UI uses the fragment to authenticate and removes it from the URL while opening the bound conversation. Houmao's native API binding is independent of the browser session.

## Sending While the Browser Is Active

The manager and gateway share one managed prompt reservation. The owner checks Kimi's live active prompt and pending queue immediately before sending. If it sees active or pending work, it refuses the ordinary prompt before sending. The browser can still start a turn after the check. In that case, Houmao reports the same prompt as queued if Kimi queues it. A lost response is reconciled using the original prompt identity.

Select the model and any explicit `tool_params.permission_mode` (`auto`, `yolo`, or `manual`) at launch. Unattended startup fills an omitted mode with `auto`. `as_is` with an omitted field uses Kimi's native settings. Houmao applies the resolved mode to the exact native browser session before publishing it on fresh launch and explicit relaunch. Browser changes to the live permission mode persist through observation and gateway reattachment.

## Host Lifetime

Gateway detach leaves the owned Kimi Web process and browser session open. The next gateway verifies the same host and exact native conversation. Stop closes the owned process. Set `--chat-session-mode exact --chat-session-id "$native_session_id"` on an explicit relaunch to preserve the conversation.
