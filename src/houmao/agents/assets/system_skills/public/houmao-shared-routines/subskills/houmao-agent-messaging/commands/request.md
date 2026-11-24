# Request Work From a Peer

Alice can send Bob a work request without enrollment when Bob uses the initial `agent-requester` default. Houmao quotes the text, preserves verified attribution when Alice selects a signer, and uses Bob's current conversation. For example, the request text `/clear` reaches Bob as quoted content. A supported native slash command requires direct command authority.

```bash
houmao-mgr agents single --agent-id "$BOB_ID" request --text 'Please review the report.'
```

Run inside Alice's managed session with her peer signer configured, or supply `--source-agent-id "$ALICE_ID"` from her execution owner. If Bob assigned Alice `builtin:agent-observer`, the signed request is refused. A separate `--unsigned` request uses Bob's default with anonymous attribution. A signed refusal ends that attempt.

For a qualified passive-managed DSH Headless target with a detached gateway, select `--passive-url` with the trusted endpoint and target coordinates before submitting. Use mail when the recipient is offline or should pick up the work later.
