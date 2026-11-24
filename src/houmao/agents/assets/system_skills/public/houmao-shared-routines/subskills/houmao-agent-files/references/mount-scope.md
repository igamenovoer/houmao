# Logical Mount Scope and Authority

The `skills` provider requires an owner-enabled DSH Web agent running the qualified DSH `0.2.2-rc.3` build and native `standard` preset. The owner enables `managed_web_skills` before launch, with prompt mode `as_is` and native permission parameters at their defaults.

For example, the execution owner can explicitly set a dedicated DSH Web profile before launching it.

```bash
houmao-mgr project profile set --name "$PROFILE_NAME" --prompt-mode as_is \
  --tool-params '{"managed_web_skills":true}'
```

The live provider qualifies the mount for the selected runtime. Existing skill sources outside the mount do not become managed files. Discovery filters mounts to those the caller can read.

The same build supports `mcp` when the owner enables `managed_web_mcp` and approves HTTP connectors in `mcp_servers` before launch. A draft file such as `review.json` can select an approved reference with `{"connector":"review-api"}` and optionally set `enabled`. The owner controls endpoints and credentials outside the mount. Use `mounts --kind mcp` to discover this provider. Publication requires a dedicated native host.

| Operation | Current Permission on `files:<mount-id>` |
| --- | --- |
| Discover and inspect the mount, published revisions, and retained candidates | `files.read` |
| Read a publication attempt by operation ID | `files.read` |
| Open, renew, read, edit, save, or discard the caller's private draft | `files.edit` and any required lease capability |
| Publish a saved candidate | `files.push` |

The owner may separately grant reading, editing, and publication. A verified initialized empty roster permits unsigned access subject to live operation prerequisites. Keyed targets evaluate the configured default group for unsigned requests. Unsigned draft operations require their private lease capability and the admitting open epoch or default revision.

## Select the Target and Signer

Use `agents single ... files` with the target's exact selected identity. The owner-local path verifies an attached gateway from the target's runtime record. Remote callers supply `--agent-id` with `--url`, `--context-id`, `--generation`, and `--presence` from trusted deployment records. Add `--ca-bundle` if private TLS requires an independently provisioned CA. The client verifies the target before use of the signer.

Use `agents self files` inside your own verified runtime. It selects the attached gateway and current managed-self registration. Choose `--unsigned` explicitly to use open or default admission.

Choose at most one signer option.

- `--signer ABSOLUTE_PRIVATE_KEY` uses an explicit enrolled key under its owner's authority.
- `--source-agent-id SOURCE_ID` selects the configured signer for a verified, locally owned source. The source can be stopped.
- `--self-signer` selects verified managed self's configured peer signer.

The selected gateway is the target agent's direct listener. A missing, stale, or unreadable listener blocks file operations. A missing grant or a changed target identity requires trusted new evidence or owner intervention.
