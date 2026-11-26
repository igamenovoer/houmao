# Change a Live Admin Roster

## Workflow

1. Verify the selected live gateway and review the current roster mode using [Access Scope](../references/access-scope.md).
2. Confirm the intended transition and exact key. Select first-key enrollment, qualification through a current administrator, or removal of one qualification.
3. Use the appropriate proof and report the confirmation and observed mode separately.

Use the native planning tool for a roster change that requires a bounded sequence of these operations.

## Command Examples

A verified initialized empty roster gives reachable callers all supported gateway permissions within operation prerequisites. The first enrolled administrator switches the gateway to keyed mode. Use the proposed key's private half for proof of possession.

An existing Stalwart binding remains attached through first-key enrollment. An operator can also attach Stalwart after key enrollment using authorized gateway access. Protected mail policy requires independent mailbox-owner authority. For attachment and provider qualification, use the Mailbox Manager routine's online-binding guidance.

```bash
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access admin-add \
  --first --signer "$PROPOSED_PRIVATE_KEY" --public-key "$PROPOSED_PUBLIC_KEY_FILE" \
  --principal "Initial operator"
```

For a keyed roster, use a current administrator key to qualify the replacement. If switching keys while remaining keyed, confirm the replacement before removing the old qualification.

```bash
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access admin-add \
  --signer "$CURRENT_ADMIN_KEY" --public-key "$REPLACEMENT_PUBLIC_KEY_FILE" \
  --principal "Replacement operator"
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access admin-remove \
  "$OLD_KEY_ID" --signer "$REPLACEMENT_PRIVATE_KEY"
```

These examples select an attached gateway in the target owner's local execution context. For a remote live gateway, set the trusted URL, context, generation, presence, and applicable CA options described in [Access Scope](../references/access-scope.md).

Removing the last qualification reopens the roster. A removed qualification leaves the credential and principal's scoped grants in place. When the owner intends to revoke proof by that key, use `credential-revoke` in the owner-local [Policy](policy.md) workflow. If a removal receipt confirms the change and reports `admin_mode: unknown`, report that distinction and use a fresh observation of the verified target.

A first-key conflict calls for a fresh roster observation. A concurrent enrollment can have already switched the listener to keyed mode.

## Guardrails

- DO NOT remove the last administrator unless opening the roster is explicitly intended.
- DO NOT reuse stale endpoint coordinates or select an unrelated key on proof failure.
- DO NOT repeat a confirmed mutation to recover an uncertain roster observation.
