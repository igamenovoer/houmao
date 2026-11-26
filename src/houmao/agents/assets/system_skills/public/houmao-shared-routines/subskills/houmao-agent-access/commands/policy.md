# Manage Retained Policy, Built-In Groups, Role Templates, and `self-key`

## Workflow

1. **Select the target agent and verify caller authority**: owner-local policy commands (`--retained`) and detached passive-listener updates (`--passive-url`) work with the gateway detached; live gateway calls use verified local records or explicit `--url`, `--context-id`, `--generation`, `--presence`, and `--ca-bundle` coordinates.
2. **Inspect before or after changes** using `access list` (shows current `admin_mode` roster posture, `default-group`, principals, key fingerprints, grants, and roles) or `access explain PRINCIPAL RESOURCE ACTION [--key-id KEY_ID]`.
3. **Apply only the requested mutation**: principal/key enrollment, `grant`/`revoke`, `role-put` (explicit permissions or `--template --resource`), `role-assign`/`role-revoke`, `default-group set`, or `self-key {rotate|revoke}`. Authenticate any peer public key through a trusted channel before enrolling.
4. **Report policy revision and immediate-admission stderr feedback**: `grant` and `revoke` emit stderr guidance explaining whether open-roster admission or another rule still governs at that policy revision, and distinguish retained policy changes from live-only operation checks.

Use the native planning tool when an owner request spans several of these supported policy operations.

## Principals, Keys, Grants, and `self-key` Lifecycle

```bash
policy=(houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access)
"${policy[@]}" list
"${policy[@]}" principal-add reviewer --kind agent --label "Reviewer" --logical-agent-id "$SOURCE_AGENT_ID"
"${policy[@]}" credential-enroll reviewer --public-key "$SOURCE_PUBLIC_KEY_FILE"
"${policy[@]}" grant reviewer "$MOUNT_RESOURCE" files.read
"${policy[@]}" explain reviewer "$MOUNT_RESOURCE" files.read
```

| Intent | Scoped `access` Command |
| --- | --- |
| Inspect roster mode, `default-group`, keys, grants, and roles | `list` |
| Define a role from exact permissions | `role-put ROLE_ID --permission RESOURCE ACTION` (repeatable) |
| Define a role from a built-in resource template | `role-put ROLE_ID --template TEMPLATE --resource RESOURCE [--action ACTION]` |
| Assign or remove a role / direct grant (`--expires-at` optional) | `role-assign PRINCIPAL ROLE_ID`, `role-revoke PRINCIPAL ROLE_ID`, `revoke PRINCIPAL RESOURCE ACTION` |
| Rotate or revoke a peer key | Enroll authenticated replacement key on the principal first, then `credential-revoke OLD_KEY_ID` (revoking the sole admin key reopens the roster; see [Admin Roster](admin-roster.md)). |
| Rotate or revoke the target's `managed-self` key | `self-key {rotate\|revoke} [--retained \| --url ... --context-id ... --generation ... --presence ...] [--signer ADMIN_KEY] [--expected-revision N]` |

## Built-In Group Ladder, `default-group`, and Role Templates

Houmao provides six built-in groups (`builtin:<group>` on `role-assign`, bare `<group>` on `default-group set`):

1. **`agent-observer`**: read-only status/inspection only (denies inbound peer mail and attributed `request`).
2. **`agent-requester`** *(initial keyed default for unassigned callers)*: adds inbound mail and quoted attributed `request` (`agent.request.submit`).
3. **`agent-maintainer`**: adds common versioned `skills` and `mcp` mount read/edit/push authority.
4. **`agent-operator`**: adds direct verbatim `prompt` (`agent.prompt.direct`), supported slash commands, and interruption.
5. **`agent-admin`**: includes full gateway and policy administration.
6. **`managed-self`**: bound to the target runtime's own `self-key` for supported self-scoped non-admin actions.

Configure `default-group` through one explicit path (live `--url`, local `--retained`, or detached `--passive-url`):

```bash
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access role-assign peer-reviewer builtin:agent-observer
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access default-group set agent-observer --retained --signer "$TARGET_ADMIN_KEY"
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access default-group set agent-requester --passive-url "$TRUSTED_PASSIVE_URL" --signer "$TARGET_ADMIN_KEY"
```

With an initialized empty admin roster (`open`), reachable callers receive applicable admin permissions; once keyed, unassigned or `--unsigned` callers receive the configured `default-group`, while enrolled principals evaluate their assigned roles/grants (for example, assigning a verified caller `builtin:agent-observer` denies mail and `request` even if `default-group` remains `agent-requester`).

Exact-resource `--template` options on `access role-put`:

- **Mount templates** (`--resource files:<mount-id>`): `skill-reviewer` (`files.read`), `skill-editor` (`files.read` + `files.edit`), `skill-publisher` (`files.read` + `files.push`), `skill-maintainer` (`files.read` + `files.edit` + `files.push`).
- **Mailbox, AG-UI, and plugin templates**: `mailbox-reader`, `mailbox-sender`, `ag-ui-viewer`, `ag-ui-runner`, and `plugin-actions` (with `--resource <plugin-resource> --action <declared-action>`).

```bash
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access role-put mount-editor --template skill-editor --resource "$MOUNT_RESOURCE"
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access role-put mount-publisher --template skill-publisher --resource "$MOUNT_RESOURCE"
```

## Guardrails

- DO NOT infer that a retained grant proves current live operation readiness without checking live target state.
- DO NOT enroll or grant permissions to an unauthenticated public key, or widen/revoke unrelated grants beyond the owner's request.
- DO NOT expose private `--signer` keys or generated `self-key` secret material in chat or logs.
