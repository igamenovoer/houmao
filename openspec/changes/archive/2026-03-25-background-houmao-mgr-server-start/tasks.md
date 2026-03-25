## 1. Server Start Command Behavior

- [x] 1.1 Add `--foreground` handling to `houmao-mgr server start` and keep the direct foreground path wired to the existing shared `run_server(...)` startup implementation.
- [x] 1.2 Implement the default detached start path so `houmao-mgr server start` spawns a child `houmao-server` process in the background using the same resolved startup flags.
- [x] 1.3 Add reuse-aware startup logic that detects an already-healthy `houmao-server` on the requested base URL and reports that instance instead of spawning a duplicate listener.

## 2. Detached Startup Reporting And Ownership

- [x] 2.1 Add launcher-side helpers/models for detached startup results, including success state, resolved URL, server identity metadata, and failure detail fields.
- [x] 2.2 Redirect detached child stdout/stderr into stable server-owned log files under the resolved server root and include those paths in failure reporting when appropriate.
- [x] 2.3 Add bounded startup waiting that verifies `houmao-server` health before reporting success and returns a clear unsuccessful result when the child exits early or never becomes healthy.

## 3. Verification

- [x] 3.1 Update unit coverage for `houmao-mgr server start` to assert default detached behavior, `--foreground` behavior, and structured startup-result output.
- [x] 3.2 Update integration coverage for server lifecycle commands to assert detached startup success, already-running reuse behavior, and unsuccessful detached startup reporting.
- [x] 3.3 Run the relevant test slices for server lifecycle behavior and confirm the updated command still interoperates with `houmao-mgr server status` and `houmao-mgr server stop`.

## 4. Documentation

- [x] 4.1 Update pair/operator docs and CLI reference examples so `houmao-mgr server start` is documented as detached-by-default with `--foreground` as the explicit attached mode.
- [x] 4.2 Document the detached startup result fields and the owned log locations operators should inspect when startup fails.
