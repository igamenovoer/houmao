## Why

Milestone 1 exposed AG-UI attachment routes, but `/v1/ag-ui/runs` still rejects task submission. Houmao needs the next per-agent gateway milestone so an AG-UI or CopilotKit client can submit one task to an existing Houmao agent and receive a protocol-compatible stream, including structured graphics artifacts.

## What Changes

- Replace the `/v1/ag-ui/runs` unavailable response with an AG-UI SSE run stream that accepts `RunAgentInput`.
- Convert AG-UI messages, state, context, resume data, and whitelisted forwarded props into a deterministic Houmao prompt.
- Admit AG-UI runs through existing per-agent gateway request controls, including busy and availability checks.
- Map Houmao headless canonical events and lower-fidelity TUI observations into AG-UI lifecycle, text, activity, tool, and terminal events.
- Add a typed `houmao_render_graphic` graphics artifact path that streams as CopilotKit-compatible AG-UI tool-call events.
- Update AG-UI capabilities so run submission and generated graphics are reported accurately when supported, while frontend tool execution, state deltas, Open Generative UI, and unsupported multimodal input remain disabled.
- Preserve lifecycle semantics: GUI disconnect detaches from the stream by default and does not stop, abort, interrupt, restart, or shut down the Houmao agent.

## Capabilities

### New Capabilities
- `per-agent-ag-ui-run-streaming`: Accepts AG-UI run requests through the live per-agent gateway, admits them through Houmao's existing request controls, and streams mapped AG-UI events.
- `ag-ui-copilotkit-graphics`: Defines and streams typed Houmao graphics artifacts as CopilotKit-renderable AG-UI tool-call sequences.

### Modified Capabilities
- `per-agent-ag-ui-attachment`: Changes `/v1/ag-ui/runs` from a deterministic unavailable route to a supported AG-UI run stream and updates capability discovery accordingly.

## Impact

- Affected API: `POST /v1/ag-ui/runs` changes from `501` unavailable to `text/event-stream` when input is valid and the target agent can admit work.
- Affected modules: `src/houmao/ag_ui/*`, `src/houmao/agents/realm_controller/gateway_service.py`, and gateway runtime observation helpers needed by the AG-UI service.
- New tests: focused unit coverage for prompt conversion, run admission, stream events, headless/TUI mapping, graphics artifact validation, capability updates, and disconnect behavior.
- Existing AG-UI dependency remains `ag-ui-protocol>=0.1.19,<0.2`; no new runtime dependency is expected for this milestone.
