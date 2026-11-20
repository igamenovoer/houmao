# Use a Live Gateway

Check `gateway status` on the intended worker. Use scoped `gateway attach` when the worker needs explicit prompt admission, gateway TUI tracking, reminders, or mail notifications. Verify `gateway_health` is `healthy`. Manage the gateway through the worker's owner route. Ordinary agent lifecycle controls also work through that route when the gateway is detached.

For a live supported Web agent, run selected-agent `gateway web-entry` from the owner context with an enrolled admin signer configured. Keep the one-time link private. Open it within 60 seconds in a browser that can reach both the owner-local gateway and native app. Kimi opens the bound conversation. In DSH, select the managed conversation in the native sidebar. The bare browser entry URL also offers interactive login.

`houmao-mgr agents single --agent-id "$agent_id" gateway --help` shows the command groups. [Gateway Lifecycle](https://igamenovoer.github.io/houmao/reference/gateway/operations/lifecycle/) · [Open a Live Web Agent](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/#open-a-live-web-agent)
