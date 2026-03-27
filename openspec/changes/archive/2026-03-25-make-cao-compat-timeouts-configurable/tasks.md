## 1. Client Timeout Split

- [x] 1.1 Extend `CaoRestClient` and `HoumaoServerClient` to carry separate general and create-operation timeout budgets, keeping ordinary requests at 15 seconds and defaulting compatibility create operations to 75 seconds.
- [x] 1.2 Route `create_session()` and `create_terminal()` through the create-operation timeout budget and add unit coverage for default and overridden timeout selection.

## 2. Pair Launch Override Surface

- [x] 2.1 Add `--compat-http-timeout-seconds` and `--compat-create-timeout-seconds` to `houmao-mgr cao launch` and the session-backed top-level `houmao-mgr launch` path, with environment-variable fallback from `HOUMAO_COMPAT_HTTP_TIMEOUT_SECONDS` and `HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS`.
- [x] 2.2 Reject compatibility timeout flags on top-level `houmao-mgr launch --headless` and update CLI tests to cover namespaced launch overrides, top-level TUI launch overrides, env fallback, and native-headless rejection.

## 3. Server Compatibility Startup Config

- [x] 3.1 Add compatibility startup timing fields to `HoumaoServerConfig` and matching `houmao-server serve` options for shell readiness, provider readiness, polling intervals, and Codex warmup while preserving the documented defaults.
- [x] 3.2 Update the compatibility control core startup path, tmux controller, and provider adapters to consume config-backed timing values instead of inline literals, including support for `compat_codex_warmup_seconds = 0.0`.
- [x] 3.3 Add unit coverage for server config validation and compatibility startup timing resolution across default and overridden settings.

## 4. Documentation And Regression Coverage

- [x] 4.1 Update pair and server docs to describe the new timeout override surfaces and explain how client create timeout relates to server compatibility startup waits.
- [x] 4.2 Run focused regression coverage for detached compatibility launch and confirm the default healthy path no longer times out during session creation.
