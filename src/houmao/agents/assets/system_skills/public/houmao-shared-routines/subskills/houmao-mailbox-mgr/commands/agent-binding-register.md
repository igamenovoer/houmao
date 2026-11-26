# Join Offline Mail Without Relaunch

## Workflow

1. Preserve the actor frame and explicit agent or verified-self target.
2. Select the configured local registry or authorized remote connection and private files.
3. Run offline join below without restarting the body or changing online mail.
4. Report the committed binding and reconcile a partial publication through the same owner claim.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Procedure

Preserve the actor frame from the parent. An admin selects an explicit agent; a verified agent can target self. Joining offline mail preserves the online slot and the agent body.

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mailbox offline join [--mailbox-root <configured-store>] [--address <address>]
<chosen houmao-mgr launcher> agents self mailbox offline join [--address <address>]
```

The owner is the persisted `agent_id`. A friendly name can supply an ordinary `<agent-name>@houmao.localhost` address, but never generates an owner ID. Local membership operations must use the selected registry's configured store; a mismatched project/default root fails instead of creating another group.

For a remote registry, require its exact HTTPS or tunneled loopback URL, requested address, and explicit private member/admin credential files. The member file is prepared before enrollment and reused on retry:

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mailbox offline join --registry-url <url> --address <address> --credential-file <private-member-file> --admin-credential-file <private-admin-file>
```

Protected filtering requires a separate trusted registry with exclusive write access to the mailbox store. A shared writable root cannot qualify. For operator setup, open the Offline Registry protected recipient filtering guide with `houmao-mgr manual`. Remote agents do not select registry-host filesystem paths or symlink targets. Credentials stay outside tracked files and discovery output. A known agent ID is not authorization.

An address owned by another agent conflicts. Join has no force, stash, principal override, or overwrite confirmation option. Same-owner retries reuse the registration. If registry enrollment committed but local publication failed, report the committed state and reconcile with status or the same join inputs; never enroll a replacement identity.

Report binding ID, revision, activation state, and any reconciliation warning. Body restart and native skill hot-reload are unnecessary; missing static skill siblings use the maintained scoped API prompt fallback.
