## 1. `houmao-server` Compatibility Contracts And Child CAO Lifecycle

- [ ] 1.1 Add `houmao-server` HTTP models for the full supported `cao-server` route surface, additive compatibility-safe request/response extensions, Houmao-owned new endpoints, and child-CAO metadata, using `pydantic` models wherever practical
- [ ] 1.2 Add child `cao-server` lifecycle management, ownership metadata, derived-port (`public_port + 1`) handling, Houmao-owned internal child-storage setup, and server persistence for current-instance state
- [ ] 1.3 Add a local `houmao-server` entrypoint implemented with Python `click` plus a client layer for health, session, terminal, and Houmao extension operations, with commands split across smaller modules rather than one giant CLI file
- [ ] 1.4 Define and document the v1 persistence boundary: which existing artifacts remain filesystem-authoritative, which stay filesystem-backed only as transitional compatibility state, and which become memory-primary under `houmao-server`
- [ ] 1.5 Pin CAO parity for this change to `https://github.com/imsight-forks/cli-agent-orchestrator.git@0fb3e5196570586593736a21262996ca622f53b6` and reference that exact source in compatibility docs and verification

## 2. Core Server Runtime And Watch Workers

- [ ] 2.1 Implement the `houmao-server` process with full supported `cao-server` API route mapping and server-owned terminal registries
- [ ] 2.2 Implement persistent per-terminal watch workers and raw-observation, owned-work, external-activity, and operator-state reduction
- [ ] 2.3 Implement Houmao new endpoints for terminal state and history inspection plus additive optional request/response extensions where needed without breaking CAO-compatible callers
- [ ] 2.4 Keep live control-plane state memory-primary inside `houmao-server` and emit filesystem mirrors only where compatibility or migration requires them
- [ ] 2.5 Keep shared registry files as a v1 compatibility bridge while designing future agent-discovery authority around `houmao-server` query surfaces rather than raw registry-file lookup
- [ ] 2.6 Add a first-class runtime backend kind `houmao_server_rest` plus dedicated persisted manifest and server-backed session metadata for `houmao-server` sessions
- [ ] 2.7 Add dedicated gateway attach metadata for `houmao_server_rest` sessions and keep child-CAO adapter details out of runtime-owned persisted contracts

## 3. Child CAO Dispatch Layer

- [ ] 3.1 Implement the v1 child-CAO dispatch layer for session lifecycle, terminal lifecycle, input, output, interrupt, inbox, and connectivity checks
- [ ] 3.2 Preserve full supported `cao-server` request and response behavior for the compatibility route surface while dispatching most work to the child `cao-server`, allowing only additive optional Houmao extensions
- [ ] 3.3 Keep child-CAO dispatch details internal so `houmao-server` remains the public server authority, the child port is always derived as `public_port + 1`, and no user-facing child-port override is introduced
- [ ] 3.4 Keep child-required on-disk support state under Houmao-owned internal server roots rather than exposing a user-facing CAO-home contract, while treating child-launch pid and ownership artifacts as internal compatibility or debug views
- [ ] 3.5 Document and enforce that `houmao-server` compatibility is part of the supported `houmao-server + houmao-srv-ctrl` pair and that mixed usage with raw `cao` is unsupported

## 4. `houmao-srv-ctrl` CAO-Compatible Wrapper

- [ ] 4.1 Add `houmao-srv-ctrl` as a Python `click`-based full supported-`cao`-compatible command family that delegates most commands to the installed `cao` executable while allowing only additive optional Houmao extensions, using modular command files rather than one giant CLI module
- [ ] 4.2 Implement successful live-agent launch registration from `houmao-srv-ctrl` into `houmao-server`
- [ ] 4.3 Preserve the existing `houmao-cli` role and keep it outside the CAO-compatible service-management surface
- [ ] 4.4 Document and enforce that `houmao-srv-ctrl` compatibility is part of the supported `houmao-server + houmao-srv-ctrl` pair and that mixed usage with raw `cao-server` is unsupported
- [ ] 4.5 Materialize Houmao-owned runtime session roots and manifests after successful delegated `houmao-srv-ctrl launch` runs, using `backend = "houmao_server_rest"`
- [ ] 4.6 When transitional registry publication is in scope for delegated launches, publish runtime pointers that reference those Houmao-owned artifacts

## 5. Runtime Integration

- [ ] 5.1 Add an opt-in `houmao-server` REST-backed runtime mode with manifest persistence for server base URL and terminal identity
- [ ] 5.2 Route `houmao-server` session inspect, prompt, control-input, interrupt, and stop flows through `houmao-server`
- [ ] 5.3 Preserve existing direct CAO flows while `houmao-server` remains opt-in

## 6. Verification And Docs

- [ ] 6.1 Add parity coverage against the pinned `cao-server` source of truth for the full supported HTTP API, including request handling, status codes, CAO-defined response fields, additive-extension safety, child-CAO lifecycle, watch-worker lifecycle, and runtime routing
- [ ] 6.2 Add parity coverage against the pinned `cao` CLI source of truth for the full supported command family through `houmao-srv-ctrl`, including exit status, user-visible output shape, additive-extension safety, and alias-style drop-in usage
- [ ] 6.3 Add documentation that the supported replacement is `houmao-server + houmao-srv-ctrl` for `cao-server + cao`, and that mixed pairs are unsupported
- [ ] 6.4 Add reference docs describing `houmao-server`, `houmao-srv-ctrl`, the first-class `houmao_server_rest` persisted backend identity, the child-CAO shallow-cut architecture, the hidden Houmao-owned child-storage model, the filesystem-vs-memory persistence boundary, the transitional shared-registry bridge, and the migration path toward eventual CAO replacement
