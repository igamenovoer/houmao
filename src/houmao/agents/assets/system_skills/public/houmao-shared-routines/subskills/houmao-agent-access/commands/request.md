# Make a Signed Peer Request

## Workflow

1. Identify the explicit target and requested supported JSON operation. Select verified managed self or an explicitly owned local source.
2. Verify target selection and trust using [Access Scope](../references/access-scope.md). Confirm the configured source signer and that the target owner enrolled the intended caller.
3. Use `access request` with the exact method, route, and supported body. Report the returned evidence or the specific proof, policy, or target failure.

If the request needs several supported operations, use the native planning tool and preserve the same verified target and caller scope throughout that sequence.

## Command Example

From a verified managed source, use trusted coordinates supplied by the target deployment. Add `--ca-bundle "$TARGET_CA_BUNDLE"` when the deployment uses a private CA.

```bash
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" access request \
  --url "$TARGET_GATEWAY_URL" --context-id "$TARGET_CONTEXT_ID" \
  --generation "$TARGET_GENERATION" --presence "$TARGET_GATEWAY_PRESENCE" \
  GET /v1/status
```

For a verified owner-local listener, omit the remote endpoint options. Add `--source-agent-id "$SOURCE_AGENT_ID"` to select an explicitly owned source, including one that is stopped. Use `--body PATH` or `--body -` for a JSON object. The CLI verifies the target before it signs the selected operation. The source gateway and tmux topology are independent of this target selection.

When a target listener or runtime changes, resolve fresh trusted coordinates. A verified caller with insufficient permission needs the exact grant from the target owner.

## Guardrails

- DO NOT attempt an operation beyond the CLI's supported gateway JSON contract.
- DO NOT automatically repeat a mutation with an uncertain result.
- DO NOT use an unauthenticated route or different signer after a rejected request.
