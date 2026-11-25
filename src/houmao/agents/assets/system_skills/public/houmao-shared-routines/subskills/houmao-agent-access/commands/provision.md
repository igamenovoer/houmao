# Provision Retained Policy

## Workflow

1. Verify the explicit target and its execution owner using [Access Scope](../references/access-scope.md).
2. Confirm the requested initial mode. Use the owner-private seed for keyed initialization or the explicit empty-roster choice for open initialization.
3. Run the selected command and report the retained policy and roster revisions alongside the resulting mode.

Use the native planning tool for a request that needs a different supported sequence within this owner workflow.

## Command Examples

Use the selected agent's owner context. The target gateway can stay detached.

```bash
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access init --seed "$SEED_FILE"
```

The seed has `schema_version: 2` and an `admin_keys` array with `principal` and `public_key` for each initial administrator. Keep the file in owner-private storage. Use the following command only when the owner explicitly chooses open access.

```bash
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access init --empty
```

For a retired registry record that prevents ordinary selection, use the preserved absolute owner runtime manifest.

```bash
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access init \
  --manifest "$TARGET_RUNTIME_MANIFEST" --seed "$SEED_FILE"
```

Initialization of an already initialized target reports its current roster. If the result is open, stderr points to `access admin-add --first` for first-admin enrollment against a verified attached gateway. For the enrollment command and signer inputs, follow [Admin Roster](admin-roster.md).

## Guardrails

- DO NOT choose an empty roster without explicit owner intent.
- DO NOT use an unverified manifest or treat initialization as a policy reset.
