# Manage Retained Policy, Built-In Groups, Role Templates, and `self-key`

## Workflow

1. **Select the target agent and verify caller authority**: owner-local policy commands (`--retained`) and detached passive-listener updates (`--passive-url`) work with the gateway detached; live gateway calls use verified local records or explicit `--url`, `--context-id`, `--generation`, `--presence`, and `--ca-bundle` coordinates.
2. **Inspect before or after changes** using `access list` (shows current `admin_mode` roster posture, `default-group`, principals, key fingerprints, grants, and roles) or `access explain PRINCIPAL RESOURCE ACTION [--key-id KEY_ID]`.
3. **Apply only the requested mutation**: principal/key enrollment, `grant`/`revoke`, `role-put` (explicit permissions or `--template --resource`), `role-assign`/`role-revoke`, `default-group set`, `default-fallback set`, or `self-key {rotate|revoke}`. Authenticate any peer public key through a trusted channel before enrolling.
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

The assignable built-in peer roles are cumulative. `role-assign` takes `builtin:<role>` for these three roles.

| Role | Additional Effects |
| --- | --- |
| `agent-requester` | Read status and send a quoted work request. |
| `agent-maintainer` | Read, edit, and publish versions on common skill and MCP mounts. |
| `agent-operator` | Send direct prompts, invoke supported slash commands, and interrupt. |

The default-group choices also include `agent-admin` and `managed-self`. Their roster and runtime memberships are system-controlled. Use an exact grant for status-only access and disable the verified principal's fallback.

```bash
policy=(houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access)
"${policy[@]}" grant peer-reviewer agent agent.status.read
"${policy[@]}" default-fallback set peer-reviewer disabled --retained --signer "$TARGET_ADMIN_KEY"
"${policy[@]}" explain peer-reviewer agent agent.status.read
"${policy[@]}" explain peer-reviewer agent agent.request.submit
"${policy[@]}" default-group set agent-requester --passive-url "$TRUSTED_PASSIVE_URL" --signer "$TARGET_ADMIN_KEY"
```

A retained built-in assignment or disabled principal fallback suppresses the default for that verified caller. Eligible unsigned requests use the target's separate anonymous admission path. An initialized open roster supplies effective administration. A migrated observer default appears as a retained status-only effect in `access list`. Select a current named group when replacing it.

Ordinary email delivery follows mailbox backend rules. For a protected binding, the mailbox owner can sign a mail-only update and relay it through `POST /v1/mail/{channel}/policy/apply`. Verify the applied revision with the trusted backend independently. Gateway grants and mail sender addresses represent separate authorities.

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
