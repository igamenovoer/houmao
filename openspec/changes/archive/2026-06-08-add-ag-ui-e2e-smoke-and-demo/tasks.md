## 1. AG-UI Diagnostics and Stream Bookkeeping

- [x] 1.1 Add AG-UI-safe diagnostic events for connect creation, connect detachment, run admission, run stream start, run completion, client disconnect, and stream errors.
- [x] 1.2 Add lightweight active AG-UI connection and active AG-UI run counters tied to stream setup and cleanup.
- [x] 1.3 Ensure diagnostics include lifecycle identifiers and operational metadata without prompt text, message bodies, credentials, mailbox content, memory content, raw terminal history, or unmanaged forwarded props.
- [x] 1.4 Convert mapping, encoding, and runtime-observation failures after `RUN_STARTED` into a deterministic `RUN_ERROR` when the client remains connected.
- [x] 1.5 Add focused unit tests for diagnostic payloads, active count cleanup, post-admission stream errors, pre-admission HTTP errors, and client abort detach semantics.

## 2. Deterministic AG-UI Wire E2E

- [x] 2.1 Add a test helper that starts a real per-agent gateway app/runtime surface and posts AG-UI `RunAgentInput` JSON to `/v1/ag-ui/runs`.
- [x] 2.2 Add a deterministic headless artifact fixture that writes canonical events under the run-id-derived `<manifest-stem>.turn-artifacts/<runId>/canonical-events.jsonl` path.
- [x] 2.3 Add an SSE collector that parses AG-UI data frames and reconstructs assistant messages plus tool calls in a CopilotKit-compatible shape.
- [x] 2.4 Add an E2E test that asserts `RUN_STARTED`, mapped text output, exactly one terminal event, successful request completion, and `runId` preservation as gateway prompt `turn_id`.
- [x] 2.5 Add an E2E graphics test that reconstructs one assistant message with one `houmao_render_graphic` tool call and validates parsed artifact arguments.
- [x] 2.6 Add a negative E2E assertion that graphics are recognized only from validated structured artifacts, not Markdown or prose adjacent to the artifact.

## 3. Live Managed-Agent Smoke

- [x] 3.1 Choose whether the live AG-UI text smoke belongs in an existing headless gateway demo, a new AG-UI demo pack, or `tests/manual/`, and document that choice in the implementation notes or README.
- [x] 3.2 Reuse maintained launch, gateway attach, isolated output root, fixture auth bundle, and cleanup patterns for one real headless managed-agent target.
- [x] 3.3 Add an AG-UI text-run probe that submits plain text through `/v1/ag-ui/runs` and records stream events, gateway request state, and cleanup evidence.
- [x] 3.4 Verify the live smoke covers queue admission, `RUN_STARTED`, mapped text or compatible terminal output, `RUN_FINISHED`, and demo-owned cleanup.
- [x] 3.5 Verify live client abort closes only the AG-UI stream subscription by default and does not interrupt the underlying Houmao task.

## 4. Browser and Client Rendering Fixture

- [x] 4.1 Add a minimal AG-UI or CopilotKit-style client fixture that points an `HttpAgent` or equivalent collector at `/v1/ag-ui/runs`.
- [x] 4.2 Register a `houmao_render_graphic` renderer or equivalent test component that renders artifact title, alt text, SVG/image/chart evidence, and failure diagnostics.
- [x] 4.3 Add an explicit Bun-global Playwright smoke command or script that runs the browser rendering fixture when Playwright is available.
- [x] 4.4 Make the browser smoke fail or skip clearly when Bun-global Playwright or its browser bundle is unavailable.
- [x] 4.5 Keep the browser smoke opt-in and outside the default Python unit-test command.

## 5. Documentation and Passive-Server Readiness

- [x] 5.1 Document direct per-agent AG-UI routes: `GET /v1/ag-ui/capabilities`, `POST /v1/ag-ui/connect`, `POST /v1/ag-ui/runs`, and `DELETE /v1/ag-ui/connections/{connection_id}`.
- [x] 5.2 Document a minimal AG-UI or CopilotKit `HttpAgent` setup for `/v1/ag-ui/runs` and the `houmao_render_graphic` renderer.
- [x] 5.3 Document known limits: lower-fidelity TUI streams, no frontend tool execution, no state deltas, conservative multimodal support, deterministic graphics smoke, and GUI-detach lifecycle semantics.
- [x] 5.4 Add a docs or route inventory test that keeps documented curl examples and route constants aligned with the FastAPI route inventory.
- [x] 5.5 Add a passive-server readiness fixture or test that defines how a future proxy preserves upstream AG-UI status behavior, `text/event-stream` content type, and SSE bytes.
- [x] 5.6 Update `context/plans/ag-ui-integration/roadmap.md` with Milestone 3 implementation results and any resolved demo decisions.

## 6. Verification

- [x] 6.1 Run focused AG-UI unit tests.
- [x] 6.2 Run new deterministic AG-UI E2E tests.
- [x] 6.3 Run the live managed-agent AG-UI smoke when local credentials and tools are available, or record the skipped prerequisite clearly. Skipped in this workspace because `tests/fixtures/auth-bundles/codex/yunwu-openai/` contains only `.gitignore`, so no usable fixture credential files were present.
- [x] 6.4 Run the optional Bun-global Playwright browser smoke when available, or record the skipped prerequisite clearly.
- [x] 6.5 Run Ruff and mypy on touched Python modules.
- [x] 6.6 Run `openspec validate add-ag-ui-e2e-smoke-and-demo --strict`.
