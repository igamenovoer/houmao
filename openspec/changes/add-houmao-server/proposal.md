## Why

Today, interactive HTTP-backed agent control in this repository depends on `cao-server`. Houmao can layer logic around CAO, but CAO still owns the server boundary, terminal lifecycle, and most always-on session authority. That makes it hard to add persistent TUI watching, Houmao-specific session state, and server-level features without either modifying CAO directly or continuing to treat CAO as the architectural center.

We also still depend on CAO's own operator CLI for CAO-native workflows. We need to reverse both server and CLI ownership. The immediate goal is a first-party `houmao-server` plus a CAO-compatible `houmao-cli`: both should be drop-in enough for shallow adoption, both may delegate most work to CAO in v1, and both should create the path to replacing CAO completely rather than remaining thin wrappers forever.

## What Changes

- Add a first-party HTTP service named `houmao-server` that acts as a drop-in replacement for `cao-server`, mapping the targeted CAO HTTP endpoint surface while also exposing Houmao-specific extension routes for watch state and history.
- Make `houmao-server` start and supervise a child `cao-server` subprocess in v1, dispatching most mapped endpoint work to that child, deriving the child CAO port as `houmao-server` port `+1`, and keeping that child port out of user-facing configuration surfaces.
- Move continuous TUI watching and state reduction into `houmao-server` so live terminals have persistent background watch workers rather than request-scoped polling only.
- Extend `houmao-cli` so it can act as a drop-in replacement for the `cao` CLI, delegating most CAO-compatible commands to the installed `cao` executable.
- Require `houmao-cli` to register newly created or launched live agents with `houmao-server` after the delegated CAO operation succeeds.
- Extend runtime launch and control flows with an optional `houmao-server` REST-backed mode that talks to `houmao-server` directly instead of to `cao-server`.

## Capabilities

### New Capabilities
- `houmao-server`: A first-party Houmao HTTP server that maps the targeted CAO HTTP endpoint surface, manages a child `cao-server` in the shallow cut, adds persistent per-terminal watch services and Houmao-specific extension routes, and is intended to outgrow CAO over time.
- `houmao-cli-cao-compat`: A CAO-compatible command surface on `houmao-cli` that delegates most work to the installed `cao` CLI while registering newly created or launched live agents with `houmao-server`.

### Modified Capabilities
- `brain-launch-runtime`: Runtime session startup and control gain an optional `houmao-server` REST-backed mode that persists `houmao-server` session identity and routes subsequent operations through `houmao-server` rather than directly through CAO.

## Impact

- New `houmao-server` package, HTTP models, child-CAO process management, watch-worker management, and local persistence under `src/houmao/`
- New CAO-backed dispatch layer that lets `houmao-server` map CAO-compatible routes while delegating most v1 work to the child `cao-server` on the internal derived port `public_port + 1`
- New `houmao-cli` CAO-compatible command family that shells out to `cao` for most operations and synchronizes launched agents into `houmao-server`
- Runtime launch/control entrypoints, manifests, and REST clients for `houmao-server`-backed sessions
- Server-owned artifact layout for process state, logs, session metadata, child-CAO ownership, and per-terminal watch histories without a user-facing child-port override contract
- Tests for server API compatibility, child-CAO lifecycle, CLI compatibility forwarding, watch lifecycle, CAO-backed delegation, and runtime integration
- Reference docs describing `houmao-server`, `houmao-cli`, their CAO-compatibility boundaries, and the migration path toward full CAO replacement
