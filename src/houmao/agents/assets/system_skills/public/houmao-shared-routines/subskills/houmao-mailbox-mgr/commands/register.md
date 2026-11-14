# Register an Offline Mailbox Account

## Workflow

1. Confirm the explicit registry/store lane and stable owner ID.
2. Check the requested address and existing ownership before enrollment.
3. Run the exclusive registration command below; preserve conflicts without takeover.
4. Report the confirmed registration, scope, and any reconciliation needed.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Procedure

Use generic or project mailbox registration for deliberate local administrative enrollment. For an existing managed body, use the offline join action instead. Registration requires the full address and owner principal ID; for a Houmao agent, that owner is its persisted `agent_id`.

```bash
<chosen houmao-mgr launcher> mailbox register --address <address> --principal-id <agent-id> [--mailbox-root <configured-store>]
<chosen houmao-mgr launcher> project mailbox register --address <address> --principal-id <agent-id>
```

The selected store must match the selected registry configuration. Registration claims ownership atomically. Another owner's address conflicts; repeating the same owner/address claim is idempotent. Force, stash, overwrite prompts, and `--yes` cannot bypass ownership. Release an old registration explicitly before assigning a fresh registration to another owner.

Ordinary managed-agent addresses use `<agent-name>@houmao.localhost`; `HOUMAO-*` local parts under that domain remain reserved for system principals. Do not preregister a new launch's derived address under a guessed name-derived ID. Resolve its stable owner first or let launch own the registration.

Report the registration ID and confirmed ownership. Do not claim that local enrollment alone makes a remote agent's runtime paths accessible or grants body lifecycle control.
