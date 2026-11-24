# Versioned Gateway File Edits

Use `houmao-mgr agents single … files` to edit an authorized peer mount and `houmao-mgr agents self files` within your own managed runtime. The gateway exposes logical paths, keeps drafts and saved commits in the target owner’s private storage, and activates a candidate only through a separate push. Peers can work across OS accounts and tmux servers using the same command. [Gateway Authorization Policy](authorization-policy.md)

## Enable and Discover the Mount

The first mount is `skills`, an owner-enabled provider for the bound DSH Web agent. Set `managed_web_skills` in the DSH tool parameters before launch. The provider requires the qualified `0.2.2-rc.3` DSH build and native `standard` preset. Use `as_is` with the permission parameters left at their native defaults. The native adapter reports the mount only while it can verify the provider for the current execution. Existing skill sources stay outside this mount. [DSH Web Compatibility](../../run-phase/dsh-web.md), [Launch Profiles](../../../getting-started/launch-profiles.md)

```bash
houmao-mgr project profile set --name dsh-browser --prompt-mode as_is \
    --tool-params '{"managed_web_skills":true}'
```

On the target owner’s account, discovery verifies the selected agent’s attached gateway from its runtime record. Use `--signer` with an enrolled key for keyed mode. Omit the signer for an initialized open roster. Open mode grants every reachable caller all supported mount permissions, while anonymous draft changes still require their private lease capability.

```bash
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" files \
    --signer "$TARGET_ADMIN_KEY" mounts
```

Each visible mount has a `mount_id`, `kind`, canonical `resource` (`files:<mount-id>`), supported `actions`, and `published_commit`. Discovery filters mounts using the caller’s current `files.read` permission. A fresh home can have a different mount ID even when the display name stays `skills`. The CLI reports missing gateway or proof errors and exits. The owner controls gateway attachment and launch separately.

The same DSH Web build and preset support a separate MCP declaration mount. Enable `managed_web_mcp` before launch and define the approved HTTP connectors in `mcp_servers`. For example, `{"managed_web_mcp":true,"mcp_servers":[{"name":"review-api","type":"http","url":"https://review.example/mcp"}]}` gives a maintainer the option to select `review-api`. An owner can supply authentication through the connector’s `headers` references to the private credential source. Each draft entry is a file named for its server, such as `review.json`, containing `{"connector":"review-api"}`. Change the approved reference to replace its connection, set `enabled` to `false` to disable it, or delete the file to remove it. Candidate files accept only `connector` and optional `enabled`. `files mounts --kind mcp` reports unsupported when the gateway has no qualified MCP provider. MCP publication requires a dedicated live native host and leaves global native configuration and other mounts outside its scope.

Within the target runtime, `houmao-mgr agents self files mounts` verifies the attached gateway and signs with the current managed-self registration. Use `--unsigned` to request the target’s open or configured default policy explicitly. A missing self credential produces an error. On a peer command, `--self-signer` continues to select the caller’s stable peer key.

## Enroll a Peer and Select Its Signer

Enroll the peer’s public key on the target as a stable agent principal using `access principal-add` and `access credential-enroll`. The peer can export its configured public key and fingerprint with `agents self access public-key`. Grant actions on the exact resource from mount discovery. For example, the target owner can let a reviewer inspect and edit drafts, then grant `files.push` separately to a publisher. [Enroll and Grant Access to a Peer](authorization-policy.md#enroll-and-grant-access-to-a-peer)

```bash
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access grant reviewer \
    "files:$MOUNT_ID" files.read
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access grant reviewer \
    "files:$MOUNT_ID" files.edit
houmao-mgr agents single --agent-id "$TARGET_AGENT_ID" access explain reviewer \
    "files:$MOUNT_ID" files.edit
```

`access explain` can show a retained grant while the gateway is detached. Live applicability remains unresolved when the target mount cannot be verified.

From another account, use the target URL, execution context, runtime generation, and listener presence obtained through a trusted channel. Supply an independently provisioned CA bundle if the target uses private TLS. The client verifies the gateway before it uses the peer key. Absolute owner-private paths work with `--signer` independently of the source agent’s runtime. Use `--source-agent-id` to select a locally configured peer signer, including from a stopped agent, or `--self-signer` to use the current managed source’s peer signer. Select one signer mode per command. [Gateway Access and Remote Deployment](access.md)

```bash
files=(houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" files
    --url "$TARGET_GATEWAY_URL" --context-id "$TARGET_CONTEXT_ID"
    --generation "$TARGET_GENERATION" --presence "$TARGET_GATEWAY_PRESENCE"
    --ca-bundle "$TARGET_CA_BUNDLE" --signer "$REVIEWER_KEY")
"${files[@]}" mounts
```

## Edit and Save a Draft

Use the exact mount ID and published commit from discovery as `MOUNT_ID` and `BASE_COMMIT`. `lease open` creates a private draft at that base. The response gives the `draft_id`, base, expiry timestamp, and opening actor. The mount accepts one renewable draft lease at a time. Saving a commit releases the lease. Aborting or letting the lease expire discards its draft changes.

```bash
"${files[@]}" --mount "$MOUNT_ID" lease open --expected-base "$BASE_COMMIT"

# Set DRAFT_ID from the lease-open response.
draft=("${files[@]}" --mount "$MOUNT_ID" --draft "$DRAFT_ID")
"${draft[@]}" mkdir review
"${draft[@]}" write review/SKILL.md --from-file ./SKILL.md
"${draft[@]}" diff
"${draft[@]}" commit --message 'Add review skill'
```

The example skill file starts with YAML front matter containing `name: review` and a nonempty `description`. `write --from-file -` reads standard input. `rename PATH DESTINATION`, `delete PATH`, `lease renew`, and `abort` operate on the selected draft. Anonymous lease opens return a `lease_capability`. Store it promptly in an owner-private file outside the checkout and add `--lease-capability-file "$LEASE_CAPABILITY_FILE"` to subsequent draft commands. Avoid printing or logging that secret in automated runs. A renewed lease retains the original capability.

Commit returns the saved `commit_id`, its base, author, committing actor, and target gateway committer. The gateway records the verified logical peer even when it writes files under a different Linux account. A draft opened unsigned has anonymous authorship. The running agent continues to use the published tree while the draft and candidate exist.

Use `files --mount ID list [DIRECTORY]` and `read PATH` to inspect the current publication. Add `--revision COMMIT` to pin a published revision. `read` returns `content_base64`. Add `--draft DRAFT_ID` at the group level for private `list`, `read`, and `diff`. With `files.read`, review saved candidates using `history --candidates` or `diff COMMIT`. Plain `history` shows published ancestry. Use `--after` with the returned `next_after` to continue a paginated list, diff, or history.

## Push and Reconcile

Select a caller with `files.push` and submit the exact saved `commit_id` from the commit response, using its recorded base. An operator can publish another caller’s candidate, including an anonymous one. The push receipt attributes the publisher separately from the author kept in Git history.

```bash
publisher=(houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" files
    --signer "$TARGET_ADMIN_KEY" --mount "$MOUNT_ID")
"${publisher[@]}" push "$CANDIDATE_COMMIT" --expected-base "$BASE_COMMIT"
"${publisher[@]}" status "$OPERATION_ID"
```

This publisher example uses an owner-local gateway. Remote publishers use the same trusted endpoint fields as remote reviewers. The client generates a fresh operation ID by default. Supply `--operation-id` to record the intended ID before making the request. `status OPERATION_ID` uses `files.read` and reads the existing attempt without resubmitting it.

| Outcome | What to do |
| --- | --- |
| `published` | Read `published_commit`, `effective_commit`, `activation`, `native_settled`, and `native_ready` separately. Publication identifies the visible tree. Native effectiveness and readiness can have different evidence. |
| `busy` | The candidate stays saved. After the target is ready, make an explicit new attempt with a fresh operation ID. |
| `queued` | The gateway is waiting for an idle maintenance boundary. Read the retained receipt through `status`. |
| `conflict` | Recheck the selected target and published base. If the base changed, open a fresh draft at the current base and apply the intended changes there. |
| `unconfirmed` | Use `status` with the original operation ID printed by the CLI. An uncertain request may already have taken effect. |
| `pending` or `unknown` | Use `status` for the best available evidence while the owner resolves the attempt. |

An immediate `push` exits successfully when its receipt confirms publication. To publish during your own active turn, submit `houmao-mgr agents self files --mount "$MOUNT_ID" push "$CANDIDATE_COMMIT" --expected-base "$BASE_COMMIT" --when-idle`. Successful exit can report that the intent is queued. Use the operation ID with `agents self files --mount "$MOUNT_ID" status`. A listener replacement, managed-self rotation, or changed base can retire the queued intent. The saved candidate remains available, and any new attempt takes a fresh operation ID. To restore earlier contents, save and push a new commit based on the current publication.
