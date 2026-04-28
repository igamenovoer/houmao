## Why

Houmao-owned managed-agent sessions currently assume the primary tmux surface can always be addressed as `session:0.0`, but tmux lets users configure `base-index` and `pane-base-index`, causing fresh launches to fail before the managed agent becomes live. The runtime should keep the contract that Houmao's primary agent window is window `0` while persisting tmux object handles for reliable control, capture, prompt submission, and recovery.

## What Changes

- Normalize Houmao-owned tmux launches so the primary managed-agent window is index `0` even when user tmux defaults create the bootstrap window at another index.
- Capture and persist the tmux object handles for the primary agent surface, including the primary window id and primary pane id.
- Route runtime operations through the persisted pane/window handles when available, while validating that the handles still satisfy the primary window `0` contract.
- Refresh stale handles from the contractual primary surface when possible and fail explicitly when the primary window authority is missing or ambiguous.
- Preserve the existing join contract that adopted sessions use tmux window `0`, pane `0` as the canonical adopted surface, while persisting discovered handles for later operations.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `tmux-integration-runtime`: Define primary managed-agent surface normalization, durable tmux object-handle persistence, validation, and stale-handle recovery semantics.
- `houmao-mgr-agents-launch`: Require launch to succeed under non-zero tmux default window/pane base indexes by establishing the primary window `0` authority before publishing managed-agent metadata.
- `houmao-mgr-agents-join`: Require join to persist live tmux handles for the adopted window `0`, pane `0` surface while keeping the existing canonical adoption contract.

## Impact

- Affected runtime modules include tmux primitives, headless/local-interactive backends, manifest boundary models and schemas, managed-agent registry publication, server fallback interruption, and tmux-backed control/capture paths.
- Tests need coverage for `base-index 1`, `pane-base-index 1`, stale persisted handle refresh, launch rollback, relaunch, join, and runtime operations targeting `%pane_id` rather than `session:0.0`.
- Existing manifests without primary tmux object handles should remain readable; the runtime can resolve and persist handles on the next launch, resume, relaunch, or control operation.
