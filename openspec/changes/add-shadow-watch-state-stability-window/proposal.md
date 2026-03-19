## Why

`add-houmao-server-official-tui-tracker` now defines the primary live-tracking contract, including server-owned stability metadata and bounded recent transitions. This change is therefore narrowed to demo-only consumption and visualization of that server-owned contract instead of defining competing tracker semantics in the demo layer.

## What Changes

- Consume the server-owned tracked-state contract from `houmao-server` instead of defining a second primary tracker in the demo
- Limit demo work to optional visualization, smoothing, or presentation choices layered on top of server-owned transport/process/parse/operator/stability fields
- Treat any demo-local stability window as presentation policy only; it must not redefine the authoritative tracker contract
- Keep existing demo evidence logging only as consumer/debug output, not as the source of truth for live tracking semantics

## Capabilities

### New Capabilities
- `demo-state-visualization`: Optional demo-only visualization or smoothing of the server-owned tracker contract

### Modified Capabilities
- `state-stability-tracking`: narrowed to server-owned contract consumption rather than defining the primary tracker contract

## Impact

- Demo-facing code under `src/houmao/demo/cao_dual_shadow_watch/`
- Optional visualization helpers that consume `houmao-server` extension routes
- Demo documentation explaining that server-owned live tracking is authoritative
