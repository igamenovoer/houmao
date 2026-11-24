# Discover a Logical File Mount

## Workflow

1. Verify the selected target and choose a caller lane from [Mount Scope](../references/mount-scope.md).
2. Run `mounts` through the target's directly attached gateway.
3. Record the exact `mount_id`, `kind`, `resource`, `actions`, and `published_commit` for the intended mount.
4. If no mount is visible, report the read-authority or provider prerequisite that the evidence supports.

For a wider authorized workflow, use the native planning tool and carry the verified discovery evidence to the selected next step.

## Command Examples

This prefix selects a target accessible from its execution owner's context. For a verified initialized open roster, omit `--signer` when the intended caller is unsigned.

```bash
files=(houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" files
  --signer "$ENROLLED_KEY")
"${files[@]}" mounts
```

Within your own runtime, use `houmao-mgr --print-json agents self files mounts`. Add `--kind mcp` when you need the MCP declaration mount.

To reach another agent from verified managed self, use the peer's trusted deployment coordinates and the source's configured peer signer. Add `--ca-bundle "$TARGET_CA_BUNDLE"` for a private TLS deployment.

```bash
files=(houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" files
  --url "$TARGET_GATEWAY_URL" --context-id "$TARGET_CONTEXT_ID"
  --generation "$TARGET_GENERATION" --presence "$TARGET_GATEWAY_PRESENCE" --self-signer)
"${files[@]}" mounts
```

Use the appropriate prefix with the same caller for the selected next operation. Supported actions describe the mount interface. Each action still requires the caller's current permission. A fresh home can have a different mount ID for the same display name.

## Guardrails

- DO NOT attach a gateway or change a profile implicitly to make discovery succeed.
- DO NOT treat an empty result as proof that the target has no files.
