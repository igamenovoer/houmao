# Prepare or Bind a Mailbox

Decide which channel the worker needs. Offline mail uses the selected registry's filesystem store. Initialize that store if needed, then configure the filesystem mailbox for `project agents launch` or use selected-agent `mailbox offline join` on an existing worker. A live join preserves the body and any online binding. An address conflict calls for a different address or explicit release by its owner.

Use `mailbox online attach` to connect an existing provider account through the worker's live gateway. Keep its credential source private on the owner host. A worker can have both channels, each with its own binding and address.

Run `mail resolve-live` before sending and check the intended channel and binding. Stopping a worker leaves its offline membership in place. `houmao-mgr agents single --agent-id "$agent_id" mailbox --help` shows the binding commands. [Mailbox Setup](https://igamenovoer.github.io/houmao/reference/mailbox/quickstart/) · [Scoped Mailbox Controls](https://igamenovoer.github.io/houmao/reference/cli/agents-mailbox/)
