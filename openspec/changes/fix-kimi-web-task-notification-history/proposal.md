# Preserve Native Prompt Identity in Kimi Web

## Why

During the ten-minute CUDA team run, Houmao stopped admitting messages to one peer after Kimi recorded a background-task notification. Replaying the retained journal isolates the failure to an adapter that applies a URL path-component validator to a valid native prompt ID. All 16 timed messages addressed to that peer were still queued at cutoff.

## What Changes

- Clarify the Kimi Web contract for native prompt IDs. A journal ID identifies a prompt within the verified session. Reading it, attributing it to a managed request, and addressing it over HTTP are separate operations.
- Preserve provider-issued prompt IDs through state and history inspection. At the interrupt endpoint, serialize the captured ID as one path segment after verifying the binding, turn, and any supplied managed operation.
- Verify the user-visible result through the gateway and CCCC. A queued message can reach the same session once the notification turn finishes and the ordinary readiness checks pass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kimi-web-control` clarifies exact native identity across observation, managed correlation, and interruption, including IDs issued by background tasks.

## Impact

The implementation belongs in the Kimi Web adapter and its native HTTP client. The existing generic gateway contract already closes admission when it cannot verify native state. CCCC already retains a pending message while a recipient is busy. The proposed change uses those contracts and preserves the current CLI, timeout policy, stored journal format, and provider protocol.

The design distinguishes the confirmed adapter bug from a separate retryable B-to-C dispatch failure whose cause the run did not establish. [Run report](../../../.imsight-arts/project-mgr/agent-driven-testing/reports/20261127T201107Z-dRSNNPzf.md)
