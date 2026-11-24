# Use a Live Gateway

Check `gateway status` on the intended worker. Use scoped `gateway attach` when the worker needs explicit prompt admission, gateway TUI tracking, reminders, or mail notifications. Verify `gateway_health` is `healthy`. Manage the gateway through the worker's owner route. Ordinary agent lifecycle controls also work through that route when the gateway is detached.

For a live supported Web agent, run selected-agent `gateway web-entry` from the owner context. An open gateway issues the link without a signer. For a keyed gateway, pass `--signer` with an enrolled key that has `web.enter` or use the configured owner signer. Keep the one-time link private and open it within 60 seconds in a browser that can reach the owner-local gateway and native app.

The bare browser entry URL opens the native app directly when the gateway is open and shows the login page when keys are enrolled. Kimi opens the bound conversation. In DSH, select the managed conversation in the native sidebar.

`houmao-mgr agents single --agent-id "$agent_id" gateway --help` shows the command groups. [Gateway Lifecycle](https://igamenovoer.github.io/houmao/reference/gateway/operations/lifecycle/) · [Open a Live Web Agent](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/#open-a-live-web-agent)
