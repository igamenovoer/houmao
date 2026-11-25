# Proposal

## Why

The live skill-update test exposed three decisions the CLI makes hard to distinguish. A revoke removed a stored grant while open admission still allowed publication, a keyed denial hid the reason, and an agent mistook a saved candidate for a queued push. [Issue #97](https://github.com/igamenovoer/houmao/issues/97)

## What Changes

- Explain the immediate admission effect of a direct grant change using the same committed policy revision as its receipt. Point owners with an open roster to the existing first-admin enrollment workflow.
- Give file commands mode-aware signer guidance and retain bounded refusal reasons from the gateway's existing error response. Name the requested action and resource where the client can identify them.
- Show recovery guidance on confirmed busy pushes, including the existing `--when-idle` option for verified managed self.
- Surface retained mode and default group in human-readable selected-agent state when local owner authority is available. Show public roster mode on the gateway landing page. Keep signer labels and enrollment details in owner-local access inspection.
- Build on the current policy, explicit signer selection, browser entry, and publication contracts. Preserve default JSON payloads, exit codes, and HTTP responses. First-admin key generation belongs to a separate follow-up because it introduces private-key storage and recovery after an uncertain enrollment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-agents-scope-cli` gains grant and enrollment guidance, file signer and refusal diagnostics, busy-push hints, and owner-local policy summary rendering.
- `gateway-dashboard` displays current public roster mode alongside existing entry guidance.

## Impact

The change affects selected-agent access, files, and state commands, gateway client error decoding, and dashboard rendering. Update the CLI reference and packaged access and files guidance at the existing entrypoints. Verify the user-visible behavior against the authorization and publication cases that produced issue #97.
