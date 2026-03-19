## Why

Today, interactive HTTP-backed agent control in this repository depends on `cao-server`. Houmao can layer logic around CAO, but CAO still owns the server boundary, terminal lifecycle, and most always-on session authority. That makes it hard to add persistent TUI watching, Houmao-specific session state, and server-level features without either modifying CAO directly or continuing to treat CAO as the architectural center.

We also still depend on CAO's own operator CLI for CAO-native workflows. We need to reverse both server and CLI ownership. The immediate goal is a first-party `houmao-server` plus a CAO-compatible `houmao-srv-ctrl`: together they should be drop-in enough for shallow adoption, both may delegate most work to CAO in v1, and together they should create the path to replacing `cao-server + cao` completely rather than remaining thin wrappers forever.

## What Changes

- Add a first-party HTTP service named `houmao-server` that acts as a drop-in replacement for `cao-server`, matching the full HTTP endpoint API of the supported `cao-server` version while exposing Houmao features only through additive request/response extensions and additional new endpoints.
- Make `houmao-server` start and supervise a child `cao-server` subprocess in v1, dispatching most mapped endpoint work to that child, deriving the child CAO port as `houmao-server` port `+1`, and keeping that child port out of user-facing configuration surfaces.
- Make `houmao_server_rest` a first-class persisted runtime backend identity with dedicated manifest and gateway metadata sections instead of reusing `cao_rest`.
- Keep any child-CAO-required filesystem state under a Houmao-owned server home or runtime root so users interact only with Houmao-managed storage rather than a separate visible CAO home.
- Move continuous TUI watching and state reduction into `houmao-server` so live terminals have persistent background watch workers rather than request-scoped polling only.
- Classify current persistent artifacts into three buckets: filesystem-authoritative data that remains on disk by design, transitional filesystem-backed compatibility data that v1 still keeps on disk but is intended to move behind `houmao-server` query APIs later, and memory-primary live control-plane state that `houmao-server` owns in memory while keeping filesystem mirrors only for compatibility, debugging, or migration.
- Add a dedicated service-management CLI named `houmao-srv-ctrl` that acts as a drop-in replacement for the `cao` CLI, delegating most CAO-compatible commands to the installed `cao` executable in the shallow cut.
- Require `houmao-srv-ctrl` to register newly created or launched live agents with `houmao-server` after the delegated CAO operation succeeds and to materialize Houmao-owned session roots and manifests for delegated launches.
- Define the compatibility contract as the paired replacement `houmao-server + houmao-srv-ctrl` for `cao-server + cao`; mixed pairs such as `houmao-server + cao` and `cao-server + houmao-srv-ctrl` are explicitly unsupported in this change.
- Pin CAO parity for this change to `https://github.com/imsight-forks/cli-agent-orchestrator.git` commit `0fb3e5196570586593736a21262996ca622f53b6`, which is currently tracked locally at `extern/tracked/cli-agent-orchestrator`.
- Extend runtime launch and control flows with an optional `houmao-server` REST-backed mode that talks to `houmao-server` directly instead of to `cao-server`.

## Capabilities

### New Capabilities
- `houmao-server`: A first-party Houmao HTTP server that matches the full supported `cao-server` HTTP API, manages a child `cao-server` in the shallow cut, adds persistent per-terminal watch services, and exposes Houmao features only through additive compatibility-safe extensions and new endpoints when used as part of the supported `houmao-server + houmao-srv-ctrl` pair.
- `houmao-srv-ctrl-cao-compat`: A CAO-compatible command surface on `houmao-srv-ctrl` that delegates most work to the installed `cao` CLI while registering newly created or launched live agents with `houmao-server`, as part of the supported `houmao-server + houmao-srv-ctrl` pair.

### Modified Capabilities
- `brain-launch-runtime`: Runtime session startup and control gain an optional `houmao-server` REST-backed mode that persists `houmao-server` session identity and routes subsequent operations through `houmao-server` rather than directly through CAO.

## Impact

- New `houmao-server` package, HTTP models, child-CAO process management, watch-worker management, and local persistence under `src/houmao/`
- New CAO-backed dispatch layer that lets `houmao-server` preserve full supported `cao-server` API behavior while delegating most v1 work to the child `cao-server` on the internal derived port `public_port + 1`
- Runtime schema evolution for a first-class `houmao_server_rest` backend, including dedicated manifest and gateway attach sections that keep child-CAO details out of persisted public contracts
- Pydantic-based Python data models for new server, runtime, and compatibility payloads wherever practical so the implementation uses one consistent model style
- A persistence-boundary design where runtime homes, session manifests, mailbox data, job dirs, Houmao-owned server roots, and logs remain filesystem-authoritative, shared registry records remain on disk only as a transitional compatibility bridge, internal child-CAO support files stay hidden inside Houmao-managed roots, and gateway-like hot control-plane state plus child-launcher bookkeeping move toward `houmao-server` memory with filesystem compatibility mirrors
- New `houmao-srv-ctrl` CAO-compatible command family that shells out to `cao` for most operations, synchronizes launched agents into `houmao-server`, and materializes Houmao-owned runtime artifacts for delegated launches
- Click-based Python entrypoints for Houmao-owned CLI tools in this change, including `houmao-srv-ctrl` and the local `houmao-server` management entrypoint, with command trees split across smaller modules rather than one giant command file
- An explicit paired-compatibility contract where `houmao-server + houmao-srv-ctrl` replaces `cao-server + cao`, while mixed-pair crosstalk is unsupported
- Runtime launch/control entrypoints, manifests, and REST clients for `houmao-server`-backed sessions
- Server-owned artifact layout for process state, logs, session metadata, internal child-adapter state, and per-terminal watch histories without a user-facing child-port override or child-CAO-home contract
- Tests for full server API compatibility against the pinned `cao-server` source of truth, additive extension safety, child-CAO lifecycle, full CLI compatibility against the pinned `cao` source of truth, watch lifecycle, CAO-backed delegation, and runtime integration
- Reference docs describing `houmao-server`, `houmao-srv-ctrl`, their CAO-compatibility boundaries, and the migration path toward full CAO replacement
