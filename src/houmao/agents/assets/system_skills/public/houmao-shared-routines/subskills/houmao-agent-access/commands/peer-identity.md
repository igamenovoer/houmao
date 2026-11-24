# Select or Export a Peer Identity

## Workflow

1. Identify whether the request configures a local source or exports verified managed self.
2. For configuration, verify the selected source's execution owner and use the explicitly selected owner-private key path. For export, preserve verified self as the source.
3. Report the logical source ID, public key, and key fingerprint to the intended trusted recipient.

For a multi-step enrollment or key replacement, use the native planning tool to coordinate this workflow with [Policy](policy.md) under their respective owners.

## Command Examples

The source execution owner can select a dedicated SSH peer key for a stopped or running source. Use its absolute owner-private path.

```bash
houmao-mgr --print-json agents single --agent-id "$SOURCE_AGENT_ID" access peer-signer \
  --key "$SOURCE_PEER_KEY"
```

A verified managed agent exports its own selected public identity. This works without an attached source gateway.

```bash
houmao-mgr --print-json agents self access public-key
```

Have the target owner verify `logical_agent_id`, `public_key`, and `key_id` through a trusted channel before enrollment. A rotated local signer must be enrolled on the target for the intended principal. The managed credential for the current runtime's self operations belongs to that generation. The configured peer signer establishes identity to independent target gateways.

## Guardrails

- DO NOT send the signer path or private key when sharing a public identity.
- DO NOT claim a key has target authority until the relevant owner or live operation provides evidence.
