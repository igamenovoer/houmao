# Houmao CCCC Plugin

`houmao-cccc` is an optional distribution for an owner-bound CCCC chat connection. Install it in the same Python environment as the Houmao gateway. The core Houmao distribution does not include it.

```bash
pixi run python -m build --wheel packages/houmao-cccc
# In the gateway's environment:
python -m pip install packages/houmao-cccc/dist/houmao_cccc-0.2.0-py3-none-any.whl
```

The distribution requires a Houmao release with gateway SDK version `2`. Its `cccc` entry point uses Houmao's public plugin SDK. The `houmao-cccc` command talks to an explicitly selected loopback gateway and uses the selected caller's credentials. The plugin uses the configured CCCC Actor and provider credential.

A compatible CCCC receiver extension is required. Stock CCCC 0.4.56 does not implement the protocol. The [integration reference](../../docs/reference/gateway/cccc.md) covers the pinned source, private Actor grants, gateway attachment, commands, and delivery outcomes. Start with the [native example](../../examples/cccc-gateway/README.md).

Each plugin instance selects one preprovisioned Group, Actor, and Actor generation for one Houmao owner. CCCC retains chat history and delivery attempts. The gateway admits each offer immediately or reports refusal/failure/uncertainty. Restarting a gateway or reconnecting a receiver never resends retained chat. The original sender explicitly requests a new attempt when appropriate.

CCCC chat and deferred Mail do not consume a Houmao email slot or change the agent's canonical identity. Version 0.2 adds explicit Mail send/reply, peek, cursor, bounded read, and authoritative read-receipt lookup. Mail requires the second tracked provider patch and its complete capability gate; a chat-only provider remains usable for chat. See [the Mail contract](../../docs/reference/gateway/cccc-mail.md) before consuming a batch.
