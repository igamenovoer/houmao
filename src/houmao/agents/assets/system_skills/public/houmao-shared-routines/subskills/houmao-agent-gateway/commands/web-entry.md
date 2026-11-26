# Open a Live Managed Web Agent (`web-entry` and `open-browser`)

## Workflow

1. **Choose between `gateway web-entry` and `open-browser`** in the target agent's execution-owner context:
   - **`agents single ... open-browser`**: opens the native local browser directly for an active local Kimi Web (`--mode web`) owner without issuing a gateway bearer URL.
   - **`agents single ... gateway web-entry`**: issues one 60-second single-use bearer URL through an attached live Web gateway (`open` initialized roster or `keyed` signer with `web.enter`).
2. **Verify target and caller proof** for `web-entry`: require an explicit `--agent-id` or `--agent-name`, confirm live Web mode + attached gateway, and select either the initialized empty-roster (`open`) path or an enrolled `--signer` with `web.enter`.
3. **Run the selected command** only when the user requested browser access and can receive any `web-entry` link privately.
4. **Report safe status fields only** (never echoing the single-use `web-entry` bearer URL into shared logs, mail, or public summaries).

If the request does not map cleanly to these steps, use the native planning tool to resolve the owner context, live Web mode, and private browser handoff before executing.

## Command Shapes

```bash
# Open native browser directly for an active local Kimi Web owner
<chosen houmao-mgr launcher> agents single --agent-id "$AGENT_ID" open-browser

# Issue a 60-second single-use gateway web-entry bearer URL (open roster vs keyed web.enter)
<chosen houmao-mgr launcher> agents single --agent-id "$AGENT_ID" gateway web-entry
<chosen houmao-mgr launcher> agents single --agent-name "$AGENT_NAME" gateway web-entry --signer "$SIGNER"
```

`gateway web-entry` returns `url` and `expires_at_utc` (valid for one redemption within `60` seconds over the owner-local address or a private tunnel reaching both the gateway and native Web service). If the gateway is detached, use [lifecycle.md](lifecycle.md) only when attachment is requested.

## Guardrails

- DO NOT use `--pair-port` or an advertised public proxy URL for owner-local `web-entry` or `open-browser`.
- DO NOT expose a `web-entry` bearer `url` in shared logs, mail, prompts, or ordinary summaries, or pick a `--signer` key unasked.
