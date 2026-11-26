# Gateway Authorization Policy

Each managed agent has one gateway authorization policy for its logical agent ID and execution context. The execution owner stores the policy in a private SQLite database under the Houmao home directory. Gateway attachment and ordinary relaunch reuse this state. A launch seed supplies the initial roster and never restores a revoked key.

The policy records stable principals, enrolled public keys, admin qualifications, roles, direct grants, and audit history. Roles and direct grants name exact resources and actions in the target agent's domain. Expiring grants and role assignments stop authorizing operations when their expiry time passes, even if the policy has no newer revision. One operation can require several permissions. For example, sending mail and reading an owner file for attachment require separate permissions.

## Admin Access

Every key on the current admin roster has all supported client-facing permissions for the target agent. With an empty initialized roster, everyone who can reach the listener has the same admin permissions, including callers who supply valid proof. These permissions include owner-file attachments, installed plugin operations, and scoped Web entry when its local transport checks pass.

First-key enrollment requires proof of possession of the proposed key. The first enrollment closes open access, and removing the last admin qualification reopens it. To rotate the only admin key while keeping access keyed, add the replacement as admin before removing the old qualification. Removing an admin qualification leaves that key enrolled and preserves its principal's scoped grants. Revoking the credential also prevents that key from proving its principal.

## Peer and Self Identity

A target owner can enroll an authenticated peer public key for a logical agent and grant that principal specific permissions. The target checks the proof against its own retained enrollment. The peer can run under another OS account or relaunch without changing its grants. The target owner can enroll a replacement key on the same principal and then revoke the old key when rotating credentials.

The `managed-self` credential belongs to the current runtime generation. It authorizes the supported non-admin effects on that agent, subject to the resource and operation's checks. A new generation gets a new credential. Gateway detachment and same-generation worker restarts reuse the saved registration. See [managed-self storage and recovery](access.md#provision-and-retain-admin-access).

## Built-In Groups

Bob can enroll Alice on one stable principal and use an exact `builtin:` assignment for her verified requests. The peer groups are cumulative.

| Group | Additional Effects |
| --- | --- |
| `agent-requester` | Read Bob's status and send a quoted work request. |
| `agent-maintainer` | Read, edit, and publish versions on Bob's owner-exposed common skill and MCP mounts. |
| `agent-operator` | Send verbatim prompts, invoke supported slash commands, and interrupt. Separate permissions cover raw keys, model and session selection, and admission overrides. |
| `managed-self` | Bob's verified current runtime can use all supported non-admin effects on its own target. |
| `agent-admin` | An enrolled admin key can use all supported effects, including admin routines. |

In keyed mode, the initial default `agent-requester` provides status and work-request authority to eligible callers. For status-only access, grant Alice the exact status effect and disable her verified fallback. Eligible unsigned requests use the configured default with anonymous attribution. A retained `builtin:` assignment suppresses fallback for that principal even after its effects expire. Exact roles and grants add their effects to the applicable group. Ordinary mail follows the mailbox backend's delivery rules.

```bash
houmao-mgr agents single --agent-id "$BOB_ID" access grant alice agent agent.status.read
houmao-mgr agents single --agent-id "$BOB_ID" access default-fallback set alice disabled --retained --signer "$BOB_ADMIN_KEY"
houmao-mgr agents single --agent-id "$BOB_ID" access explain alice agent agent.status.read
houmao-mgr agents single --agent-id "$BOB_ID" access explain alice agent agent.request.submit
houmao-mgr agents single --agent-id "$BOB_ID" access default-group set agent-requester --retained --signer "$BOB_ADMIN_KEY"
```

The default and fallback setters select the attached gateway, direct `--passive-url`, or owner-local `--retained` path. A retained update works while Bob is stopped. The gateway routes are `PUT /v1/admin/default-permission-group` and `PUT /v1/admin/principals/{principal_id}/default-fallback`. The direct passive routes put the same resources under `/houmao/agents/{agent_ref}/admin/`. The five named groups in the table are available as default choices. Selecting `agent-admin` lets otherwise unassigned eligible callers perform applicable admin operations. Roster mutation still requires enrollment proof. Selecting `managed-self` confers its effects under the caller's own provenance.

`access list` shows the current default, per-principal fallback settings, revisions, roles, and enrollments. `access explain alice agent agent.request.submit` shows the decision for Alice's enrolled keys. The default and applicable principal fallback revisions fence pending effects even if Bob later restores the same values. An empty initialized admin roster authorizes all supported effects regardless of the selected default.

On upgrade, a retained `agent-observer` assignment becomes an exact status effect with its original expiry and disabled fallback for that principal. A retained observer default appears as status-only in inspection. Its replacement uses one of the current named groups.

## Bind a Role to One Resource

Bob can give Alice edit access to a single common-plugin mount and give another principal publish access. Use the canonical `files:<mount-id>` from file discovery.

```bash
houmao-mgr agents single --agent-id "$BOB_ID" access role-put skill-editor --template skill-editor --resource "$SKILL_MOUNT_RESOURCE"
houmao-mgr agents single --agent-id "$BOB_ID" access role-put skill-publisher --template skill-publisher --resource "$SKILL_MOUNT_RESOURCE"
houmao-mgr agents single --agent-id "$BOB_ID" access role-assign alice skill-editor
houmao-mgr agents single --agent-id "$BOB_ID" access role-assign reviewer skill-publisher
```

The same templates apply to an exact MCP declaration mount. Other templates cover a selected mailbox (`mailbox-reader`, `mailbox-sender`), AG-UI thread (`ag-ui-viewer`, `ag-ui-runner`), or bound gateway plugin (`plugin-actions`). Supply the exact live plugin resource and repeat `--action` for each declared action. Bob can use `access role-revoke` to remove an assignment. Use `--local` to select a retained local role whose name collides with a built-in reference.

## Migrate Prompt Grants

Inspect retained `agent.prompt` rows using `access list` and `access explain`. The gateway preserves those rows for inspection. They have retired from authorization. Grant `agent.request.submit` for quoted work, `agent.prompt.direct` for verbatim input, or `agent.command.invoke` for supported native commands as appropriate. The `agent` resource remains the exact scope for these effects. Review queued work and reminders that were admitted under the old effect before submitting replacements.

## Owner and Effect Boundaries

Owner-local policy administration uses the verified execution binding and works without an attached gateway. The private filesystem and execution context form the ownership boundary. Processes running under the same UID share that account's filesystem authority.

The gateway reads current policy at admission. A protected effect that waits for execution can revalidate the admitted actor, listener, runtime generation, and permissions at its handoff. The handoff and policy updates use the same short SQLite writer lock. Audit records include the policy revision and safe operation metadata.

## Provision a Target Policy

Run these commands in the selected agent's execution context. Choose one initial mode explicitly for a target that needs reprovisioning.

```bash
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access init --seed "$SEED_FILE"
# Or, for an intentionally open roster:
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access init --empty
```

Put the seed in owner-private storage. It contains `"schema_version": 2` and an `admin_keys` array whose entries have `principal` and `public_key` fields. For an already initialized target, `init` reports the current roster without resetting it. The target can stay detached during initialization and other owner-local policy changes.

If retired discovery metadata prevents target selection, add `--manifest "$RUNTIME_MANIFEST"` to `access init`. Use the preserved absolute `manifest.json` path under the selected owner's runtime directory. The command verifies the manifest against the selected agent and current execution owner. Normal launch refuses to initialize a policy over retained roster state from an earlier release. Use `access init` to choose the new roster explicitly.

## Enroll and Grant Access to a Peer

On the source account, create and select a dedicated SSH signing key in owner-private storage. Use an absolute path for the private key. The source owner can select the signer while the source agent is stopped.

```bash
houmao-mgr --print-json agents single --agent-id "$SOURCE_AGENT_ID" access peer-signer \
    --key "$SOURCE_PEER_KEY"
```

From inside the source managed agent, obtain the same public identity without a source gateway.

```bash
houmao-mgr --print-json agents self access public-key
```

Transfer the `logical_agent_id`, `public_key`, and `key_id` fingerprint to the target owner through a trusted channel. The target owner verifies that the public key belongs to the intended source and saves the public key in a file. Each policy assigns its own stable principal ID. The example below uses `reviewer` as the principal ID on the target.

```bash
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access principal-add reviewer \
    --kind agent --label "Reviewer" --logical-agent-id "$SOURCE_AGENT_ID"
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access credential-enroll reviewer \
    --public-key "$SOURCE_PUBLIC_KEY_FILE"
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access grant reviewer \
    agent agent.status.read
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access explain reviewer \
    agent agent.status.read
```

Use `role-put` with one `--permission RESOURCE ACTION` per effect, then use `role-assign` for a reusable permission set. `grant` and `role-assign` accept `--expires-at` as UTC Unix seconds. Inspect policy with `access list`. Remove a direct grant with `access revoke`, a role assignment with `access role-revoke`, or one key and its admin qualification with `access credential-revoke`.

`access explain` evaluates retained policy for declared gateway and passive operations. For an operation that only a live plugin host can resolve, it reports the retained assignments and leaves the operation decision unresolved. The gateway verifies runtime capabilities when it receives the request.

The source can now issue a signed request to the independently selected remote target. Obtain the target URL, execution context ID, runtime incarnation, and listener presence ID from trusted target deployment and discovery records. For a private TLS deployment, supply the independently provisioned CA bundle with `--ca-bundle`.

```bash
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access request \
    --url "$TARGET_GATEWAY_URL" --context-id "$TARGET_CONTEXT_ID" \
    --generation "$TARGET_GENERATION" --presence "$TARGET_GATEWAY_PRESENCE" \
    GET /v1/status
```

Run `access request` from the current managed source, or pass `--source-agent-id` to select a locally owned source, including a stopped one. The client verifies the selected gateway before it uses the source key. A changed target generation or listener requires a fresh trusted selection. `access request` supports protected gateway JSON operations. Use `--body` with a JSON object file or `-` for standard input.

## Change a Live Admin Roster

Use `access admin-add --first --signer "$PROPOSED_PRIVATE_KEY" --public-key "$PROPOSED_PUBLIC_KEY" --principal operator` to enroll the first key. For subsequent additions, omit `--first` and use a current admin key as `--signer`. `access admin-remove KEY_ID --signer "$CURRENT_ADMIN_KEY"` removes only the selected admin qualification. Both commands use the attached owner-local gateway by default and accept `--url` with the exact remote coordinates shown above.

After a confirmed removal, the CLI reads the current roster mode. If that observation fails, it reports `admin_mode` as `unknown` alongside the confirmed removal. The mutation runs once.
