## 1. `houmao-server` Compatibility Contracts And Child CAO Lifecycle

- [ ] 1.1 Add `houmao-server` HTTP models for the targeted CAO-compatible route surface, Houmao extension routes, and child-CAO metadata
- [ ] 1.2 Add child `cao-server` lifecycle management, ownership metadata, derived-port (`public_port + 1`) handling, and server persistence for current-instance state
- [ ] 1.3 Add a local `houmao-server` entrypoint and client layer for health, session, terminal, and Houmao extension operations

## 2. Core Server Runtime And Watch Workers

- [ ] 2.1 Implement the `houmao-server` process with CAO-compatible route mapping and server-owned terminal registries
- [ ] 2.2 Implement persistent per-terminal watch workers and raw-observation, owned-work, external-activity, and operator-state reduction
- [ ] 2.3 Implement Houmao extension routes for terminal state and history inspection

## 3. Child CAO Dispatch Layer

- [ ] 3.1 Implement the v1 child-CAO dispatch layer for session lifecycle, terminal lifecycle, input, output, interrupt, inbox, and connectivity checks
- [ ] 3.2 Preserve CAO-compatible request and response shapes for the mapped route surface while dispatching most work to the child `cao-server`
- [ ] 3.3 Keep child-CAO dispatch details internal so `houmao-server` remains the public server authority, the child port is always derived as `public_port + 1`, and no user-facing child-port override is introduced

## 4. `houmao-cli` CAO-Compatible Wrapper

- [ ] 4.1 Extend `houmao-cli` with a CAO-compatible command family that delegates most commands to the installed `cao` executable
- [ ] 4.2 Implement successful live-agent launch registration from `houmao-cli` into `houmao-server`
- [ ] 4.3 Preserve the existing Houmao runtime-management command family on `houmao-cli`

## 5. Runtime Integration

- [ ] 5.1 Add an opt-in `houmao-server` REST-backed runtime mode with manifest persistence for server base URL and terminal identity
- [ ] 5.2 Route `houmao-server` session inspect, prompt, control-input, interrupt, and stop flows through `houmao-server`
- [ ] 5.3 Preserve existing direct CAO flows while `houmao-server` remains opt-in

## 6. Verification And Docs

- [ ] 6.1 Add unit and integration coverage for server API compatibility, child-CAO lifecycle, CLI compatibility delegation, watch-worker lifecycle, and runtime routing
- [ ] 6.2 Add reference docs describing `houmao-server`, `houmao-cli`, the child-CAO shallow-cut architecture, and the migration path toward eventual CAO replacement
