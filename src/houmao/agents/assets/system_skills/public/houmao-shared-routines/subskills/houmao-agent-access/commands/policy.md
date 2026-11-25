# Manage Retained Policy

## Workflow

1. Select the target agent and verify the execution owner. Owner-local policy commands work with the gateway detached.
2. For inspection, use `list` or `explain`. For a change, confirm the exact principal, key fingerprint, resource, action, or role that the owner specified.
3. Apply only the requested enrollment, grant, role, or revocation. If enrolling a peer, authenticate its public identity through a trusted channel first.
4. Report the target, affected identifiers, and current policy evidence. Distinguish a retained assignment from a permission that only a qualified live operation can verify.

Use the native planning tool when an owner request spans several of these supported policy operations.

## Example

This enrolls a managed reviewer with a separately verified public key and grants read access to one discovered mount. Use the exact target resource returned by discovery, such as `files:<mount-id>`.

```bash
policy=(houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access)
"${policy[@]}" principal-add reviewer \
  --kind agent --label "Reviewer" --logical-agent-id "$SOURCE_AGENT_ID"
"${policy[@]}" credential-enroll reviewer --public-key "$SOURCE_PUBLIC_KEY_FILE"
"${policy[@]}" grant reviewer "$MOUNT_RESOURCE" files.read
"${policy[@]}" explain reviewer "$MOUNT_RESOURCE" files.read
```

Use `list` to show the retained principals, key fingerprints, grants, roles, and role assignments. `explain PRINCIPAL RESOURCE ACTION --key-id KEY_ID` limits the explanation to one enrolled key. A live-only operation can return an unresolved decision while the retained grant is present.

Read the recorded change and policy revision from the `grant` or `revoke` output. The stderr guidance explains whether open admission still supplies authority at that revision. In keyed mode, use `access explain` to see the relevant grant, role, and key evidence for the action. Use `access list` for the current roster mode and default group.

## Other Operations

| Intent | Scoped Access Command |
| --- | --- |
| Define the exact permission set of a reusable role | `role-put ROLE --permission RESOURCE ACTION` with one repeated option per effect |
| Assign a role | `role-assign PRINCIPAL ROLE` |
| Remove a direct grant | `revoke PRINCIPAL RESOURCE ACTION` |
| Remove a role assignment | `role-revoke PRINCIPAL ROLE` |
| Revoke an enrolled key and its admin qualification | `credential-revoke KEY_ID` |
| Rotate a peer key | Enroll the authenticated replacement key on the existing principal, then revoke the old fingerprint. |

A direct grant or role assignment accepts `--expires-at` in UTC Unix seconds. Review the current role before replacing its permission set. If a credential carries the only administrator qualification, revoking it reopens the roster. Use [Admin Roster](admin-roster.md) for live roster rotation.

## Guardrails

- DO NOT infer that a retained grant proves current live applicability.
- DO NOT grant to a public key whose principal or logical source has not been authenticated.
- DO NOT infer a broad grant or revoke unrelated assignments from a narrower request.
## Built-In Groups and the Default

Bob can assign a verified Alice `builtin:agent-observer` for status only, `builtin:agent-requester` for status, mail, and quoted requests, `builtin:agent-maintainer` to add common skill and MCP edits, or `builtin:agent-operator` to add direct prompts, supported slash commands, and interruption. Bob's current runtime uses its `managed-self` identity for supported non-admin actions. `agent-admin` includes policy administration.

```bash
houmao-mgr agents single --agent-id "$BOB_ID" access role-assign alice builtin:agent-observer
houmao-mgr agents single --agent-id "$BOB_ID" access default-group set agent-observer --retained --signer "$BOB_ADMIN_KEY"
```

Keyed Bob initially gives unassigned callers `agent-requester` without enrollment. Alice's verified observer assignment denies mail and wrapped requests. A separate unsigned request receives the configured default with anonymous attribution. With an empty admin roster, every caller receives the applicable admin permissions. Use `access list` to inspect Bob's chosen default and `access explain alice agent agent.request.submit` to examine Alice's verified authority.

For one common skill or MCP mount, get its exact `files:<mount-id>` from file discovery. `access role-put editor --template skill-editor --resource "$MOUNT_RESOURCE"` creates a role with read and edit. `skill-publisher` gives read and publish on that exact resource. Assign them separately so the editor can save a draft and the publisher can decide when to apply it.
