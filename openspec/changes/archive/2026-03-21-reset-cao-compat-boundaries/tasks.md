## 1. Server HTTP Boundary

- [x] 1.1 Move the CAO-compatible HTTP route family in `houmao-server` behind an explicit `/cao/*` router and remove root `/sessions/*` and `/terminals/*` handlers.
- [x] 1.2 Keep root `GET /health` and `/houmao/*` routes Houmao-owned, and add or preserve `/cao/health` for CAO-compatible health behavior.
- [x] 1.3 Update `HoumaoServerClient`, server query helpers, repo-owned demos, and server-side client tests so pair-owned CAO session and terminal calls target `/cao/*` through one shared compatibility client seam instead of the server root.

## 2. Runtime And Gateway Break Repairs

- [x] 2.1 Introduce an explicit CAO-compatibility client seam for `houmao-server` so `houmao_server_rest` runtime control no longer assumes root CAO routes, while persisted `api_base_url` values remain rooted at the public server authority.
- [x] 2.2 Update gateway attach and any other pair-owned session-control paths to use the shared `/cao/*` compatibility seam when targeting `houmao-server`, rather than reconstructing plain root-path CAO clients from persisted state.
- [x] 2.3 Refresh runtime, gateway, and manifest-validation tests that currently assume `houmao-server` exposes CAO routes at the root or would require persisting `/cao`-qualified base URLs.

## 3. `houmao-srv-ctrl` Command Boundary

- [x] 3.1 Replace the top-level CAO command inventory with an explicit `cao` group, and keep only Houmao-owned pair commands such as top-level `launch` and `install`.
- [x] 3.2 Make top-level `houmao-srv-ctrl install` always route through `houmao-server`, and move raw local CAO install behavior under `houmao-srv-ctrl cao install`.
- [x] 3.3 Implement session-backed `houmao-srv-ctrl cao` commands such as `launch`, `info`, and `shutdown` as pair-aware compatibility commands over the supported boundary rather than blind top-level passthrough, and preserve compatibility-significant exit-code and script-facing stdout/stderr behavior.
- [x] 3.4 Preserve the existing pair-owned launch follow-up work for session-backed launches, including live-agent registration, tmux window metadata preservation, and `houmao_server_rest` artifact materialization.
- [x] 3.5 Keep top-level `houmao-srv-ctrl launch --headless` as the canonical native headless path and verify that namespaced `houmao-srv-ctrl cao launch` remains distinct compatibility behavior.

## 4. Verification And Documentation

- [x] 4.1 Replace root-route and top-level-verb parity tests with `/cao/*` HTTP parity tests and `houmao-srv-ctrl cao ...` command-surface parity tests.
- [x] 4.2 Add or update focused tests for removed root CAO routes, removed top-level CAO verbs, pair-owned top-level install behavior, runtime/gateway routing through the explicit compatibility namespace, and repo-owned demos or demo-backed tests that instantiate `HoumaoServerClient`.
- [x] 4.3 Add regression coverage for `houmao-srv-ctrl cao launch/info/shutdown` exit codes and compatibility-significant machine-readable or script-consumed stdout/stderr behavior, without requiring byte-for-byte human-prose parity.
- [x] 4.4 Update pair reference, migration, and CLI documentation to describe the new boundary explicitly: root and `/houmao/*` are Houmao-owned, `/cao/*` is CAO compatibility, top-level `houmao-srv-ctrl` is Houmao-owned, and `houmao-srv-ctrl cao ...` is CAO compatibility.
