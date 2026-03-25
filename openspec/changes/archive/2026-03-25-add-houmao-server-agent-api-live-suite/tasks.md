## 1. Fixture And Suite Foundations

- [x] 1.1 Add a lightweight tracked `server-api-smoke` fixture family for Claude and Codex, including dedicated roles, any matching secret-free config or compatibility-profile inputs, and provider-specific recipes or blueprints, while reusing a copied `tests/fixtures/dummy-projects/mailbox-demo-python/` workdir for API-focused live runs.
- [x] 1.2 Create the canonical manual live-suite entrypoint under `tests/manual/` together with shared helper modules for isolated run-root layout, per-lane or all-lanes selection, repo-local `tmp/` default output layout plus override support, prerequisite checks for `tmux`, selected provider executables, selected fixture assets, and required credential inputs, and structured artifact/report writing.
- [x] 1.3 Implement suite-owned `houmao-server` startup and shutdown helpers that provision isolated runtime, registry, jobs, home, and log roots, wait for `GET /health` readiness before provisioning lanes, record the selected API base URL, and persist owned-server shutdown evidence after lane cleanup.

## 2. Transport Provisioning Paths

- [x] 2.1 Implement the TUI provisioning path for Claude and Codex: install the selected lightweight `server-api-smoke` profile, create the CAO-compatible session with a configurable timeout budget whose initial default is 90 seconds, call `materialize_delegated_launch()`, register the launch through the current `HoumaoRegisterLaunchRequest` model, and record lane metadata for cleanup.
- [x] 2.2 Implement the native headless provisioning path for Claude and Codex by calling `materialize_headless_launch_request()` from tracked fixtures, launching through `POST /houmao/agents/headless/launches`, and recording the returned managed-agent identity plus manifest/session-root artifact paths.
- [x] 2.3 Implement explicit lane teardown helpers that stop launched lanes through `POST /houmao/agents/{agent_ref}/stop`, perform best-effort session or tmux cleanup for partially started TUI lanes, and complete that lane cleanup phase before owned-server shutdown runs.

## 3. API Verification And Evidence Capture

- [x] 3.1 Add shared managed-agent route verification for `GET /houmao/agents`, `GET /houmao/agents/{agent_ref}`, `GET /houmao/agents/{agent_ref}/state`, and `GET /houmao/agents/{agent_ref}/state/detail`, including transport-specific assertions on `/state/detail` field `detail.transport` for all four lanes.
- [x] 3.2 Add prompt-submission verification through `POST /houmao/agents/{agent_ref}/requests` for all four lanes, with bounded polling for post-request state changes and durable headless turn inspection when a headless turn handle is returned.
- [x] 3.3 Persist per-lane HTTP request/response snapshots, launch metadata, stop results, owned-server shutdown results, and final suite summaries under the suite-owned run root so operators can inspect failures without rerunning the suite.

## 4. Operator Guidance And Verification

- [x] 4.1 Document the live-suite invocation contract, prerequisite executables (`tmux` plus selected provider CLIs), Codex API-key-mode credential expectations, supported all-lanes and per-lane selection, default repo-local `tmp/` artifact location plus override behavior, and artifact inspection paths for operators.
- [x] 4.2 Run the new live suite against a real local environment, capture the resulting artifacts, and adjust timeout budgets or cleanup behavior until the four-lane basic lifecycle is repeatable.
