## 1. App Scaffold

- [ ] 1.1 Create `apps/README.md` that explains app directories stay outside the Python package.
- [ ] 1.2 Create `apps/ag-ui-workbench/` with README, `package.json`, Vite config, TypeScript config, HTML entrypoint, source directory, test directory, and scripts directory.
- [ ] 1.3 Add scoped app dependencies and scripts for Bun-based install, development server, typecheck, build, and E2E smoke.
- [ ] 1.4 Add app styling baseline and layout containers that match a dense developer workbench rather than a landing page.
- [ ] 1.5 Verify the Python package configuration still includes only `src/houmao` in wheel builds and does not include `apps/`.

## 2. AG-UI Client Core

- [ ] 2.1 Add TypeScript AG-UI request and event types needed by the workbench, importing package types where practical and keeping fallback local shapes narrow.
- [ ] 2.2 Implement target URL normalization for direct gateway base URLs, direct run/connect URLs, and future passive-server agent AG-UI URLs.
- [ ] 2.3 Implement capabilities fetching with visible support flags for SSE, text input, state snapshots, graphics, frontend tool execution, state deltas, and multimodal input.
- [ ] 2.4 Implement AG-UI run submission that builds deterministic `RunAgentInput` payloads with thread ID, generated run ID, messages, tools, context, state, and forwarded props.
- [ ] 2.5 Implement AG-UI connect attachment that does not submit prompt text and supports stream abort.
- [ ] 2.6 Implement explicit detach cleanup for known connection IDs and no-op-safe cleanup when a connection ID is unavailable.
- [ ] 2.7 Implement SSE parsing that preserves raw event payloads and reports parse errors without crashing the app.

## 3. Event Reduction and Rendering

- [ ] 3.1 Add an event reducer for run status, transcript messages, tool calls, state snapshots, activity/custom records, errors, and raw timeline entries.
- [ ] 3.2 Render text message sequences and terminal run states from reduced AG-UI events.
- [ ] 3.3 Render state snapshots, activity/custom records, tool-call details, and raw event JSON in pane diagnostics views.
- [ ] 3.4 Render pre-admission HTTP errors and streamed `RUN_ERROR` events as visible pane errors.
- [ ] 3.5 Implement `houmao_render_graphic` reconstruction from complete AG-UI tool-call sequences.
- [ ] 3.6 Render supported `houmao_render_graphic` formats safely for the first version, with SVG visible in the deterministic smoke.
- [ ] 3.7 Render deterministic unsupported-format fallback UI while preserving raw tool-call event details.

## 4. Workbench UI

- [ ] 4.1 Implement the top-level workbench shell with a toolbar for adding panes and showing proxy/runtime status.
- [ ] 4.2 Integrate Dockview and register panel components for the pinned operator panel, agent panes, and optional event inspector panels.
- [ ] 4.3 Implement the operator panel target form, connect controls, prompt composer, run status display, transcript, and event diagnostics.
- [ ] 4.4 Implement agent pane target form, capability refresh, connect/disconnect controls, prompt composer, transcript, state view, graphics renderer, and raw event timeline.
- [ ] 4.5 Ensure operator prompt submission sends only to the configured operator target and does not fan out to other panes.
- [ ] 4.6 Ensure each pane owns independent target configuration, stream controller, event reducer state, and cleanup behavior.
- [ ] 4.7 Persist only layout and non-sensitive target metadata in local storage, and avoid persisting prompt text or stream payloads by default.
- [ ] 4.8 Add clear empty, connecting, connected, running, error, and disconnected states without in-app tutorial copy.

## 5. Local Proxy

- [ ] 5.1 Implement an app-local development proxy for capabilities, connect, run, and detach requests.
- [ ] 5.2 Add target policy helpers that allow loopback HTTP targets by default and reject disallowed protocols or hosts.
- [ ] 5.3 Preserve upstream status, response headers needed for SSE, and streaming bytes without buffering full `text/event-stream` responses.
- [ ] 5.4 Abort upstream proxy requests when the browser request aborts.
- [ ] 5.5 Surface deterministic target-policy and proxy errors to the workbench UI.

## 6. Deterministic E2E Coverage

- [ ] 6.1 Add a fake AG-UI server or Playwright route fixture that emits deterministic capabilities, connect, run, text, state, error, detach, and graphics responses.
- [ ] 6.2 Add a Playwright smoke that starts the workbench, configures the operator panel, submits one operator run, and verifies visible run evidence.
- [ ] 6.3 Add a Playwright smoke path that creates at least two agent panes, connects them to separate fake targets, and verifies event isolation between panes.
- [ ] 6.4 Add a Playwright assertion for visible `houmao_render_graphic` SVG title, alt text, and SVG content.
- [ ] 6.5 Add a Playwright assertion that closing or disconnecting a pane uses GUI detach or abort behavior and does not expect Houmao interrupt semantics.
- [ ] 6.6 Add a Playwright assertion that layout and target metadata restore after reload while prior stream payloads do not persist.

## 7. Documentation and Verification

- [ ] 7.1 Document workbench purpose, dependency setup, Bun commands, target URL examples, direct gateway setup, future passive-server URL shape, and known limits.
- [ ] 7.2 Document that the GUI does not manage Houmao agent lifecycle and that close/stop means GUI detach by default.
- [ ] 7.3 Update `context/plans/ag-ui-integration/roadmap.md` with the workbench milestone and what remains after it.
- [ ] 7.4 Run the workbench TypeScript typecheck and production build.
- [ ] 7.5 Run the deterministic Bun Playwright workbench E2E smoke.
- [ ] 7.6 Run focused Python AG-UI tests if backend contract adjustments are needed during implementation.
- [ ] 7.7 Run `openspec validate add-ag-ui-workbench-app --strict`.
