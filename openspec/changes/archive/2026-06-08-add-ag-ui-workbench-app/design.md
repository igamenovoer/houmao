## Context

The per-agent AG-UI gateway now exposes `/v1/ag-ui/capabilities`, `/v1/ag-ui/connect`, `/v1/ag-ui/runs`, and explicit connection detach routes. Backend tests and the current browser smoke prove deterministic event mapping and `houmao_render_graphic` rendering, but there is no runnable GUI that lets a developer attach to more than one live Houmao agent, inspect the raw protocol stream, and compare rendered output with AG-UI events.

This change adds a standalone app under `apps/ag-ui-workbench/`. It is not a Python runtime feature and must not be included in the wheel or sdist. The existing Hatch wheel target already includes only `src/houmao`; the workbench should keep its own JavaScript dependencies, scripts, and E2E fixtures under `apps/`.

The intended user is a Houmao developer or operator testing AG-UI conformance against already-running Houmao agents. The workbench must not create, start, stop, restart, or own managed agents.

## Goals / Non-Goals

**Goals:**

- Provide a minimal but useful AG-UI protocol workbench with a pinned operator input panel and configurable docked agent panes that can move within the app through tab and split positions.
- Let each pane independently target a direct per-agent gateway URL or a future passive-server AG-UI URL.
- Capture and render raw AG-UI events, reduced messages, state snapshots, activity/custom events, run errors, and `houmao_render_graphic` artifacts.
- Preserve GUI-detach semantics: closing a pane, aborting a stream, or using a stop button detaches the GUI stream by default and does not interrupt the Houmao task.
- Add deterministic browser E2E coverage that can run without live model credentials.
- Document and support live/manual validation against a Kimi Code headless Houmao agent when local Kimi credentials are available.

**Non-Goals:**

- Do not add a packaged GUI to the PyPI distribution.
- Do not implement Houmao agent lifecycle controls in the GUI.
- Do not replace backend AG-UI unit or integration tests.
- Do not require CopilotKit as the core runtime path for the workbench.
- Do not add frontend tool execution, Open Generative UI, or multimodal support unless the existing backend capabilities already support them.

## Decisions

### Put the app in `apps/ag-ui-workbench/`

The workbench should live under `apps/` with its own `package.json`, Vite config, TypeScript config, README, scripts, and Playwright tests.

Rationale: this keeps JavaScript dependencies isolated from the Python package and gives the GUI enough structure to evolve without changing the Houmao runtime package.

Alternative considered: place the GUI under `scripts/demo/`. That works for a one-off smoke fixture, but the requested multi-pane operator workbench is an application, not a tiny demo script.

### Use React, Vite, Bun scripts, and Dockview for in-app docking

The app should use React with Vite for a small browser application and Dockview React bindings for the pane layout. Dockview organizes content into panels and groups, exposes `DockviewApi` through `onReady`, supports `api.addPanel()`, supports tab grouping and split directions such as `above`, `below`, `left`, `right`, and `within`, and persists layouts through `api.toJSON()` and `api.fromJSON()`.

The Houmao workbench should use the docked grid behavior only. It should pass `disableFloatingGroups` to `DockviewReact`, avoid `api.addFloatingGroup()`, avoid `api.addPopoutGroup()`, omit any popout menu/action, and sanitize restored layout JSON by dropping `floatingGroups` and `popoutGroups` before `api.fromJSON()`.

Rationale: Vite keeps local development simple, and Dockview avoids hand-rolling tab and split behavior. Disabling floating and avoiding popout windows keeps every Houmao agent GUI pane inside the main workbench, which matches the desired operator model.

Alternative considered: use a custom CSS grid and tabs. That would be faster for one or two panes but would not satisfy the expected add/remove/move subwindow workflow.

Alternative considered: allow Dockview floating groups or popout windows. That conflicts with the requirement that panes stay inside the Houmao GUI rather than becoming separate windows.

### Make direct AG-UI client code the protocol source of truth

The workbench should implement a small direct client for Houmao AG-UI endpoints:

- `GET /capabilities`
- `POST /connect`
- `POST /runs`
- `DELETE /connections/{connection_id}` when a connection ID is known
- SSE frame parsing
- stream abort and cleanup
- event reduction into messages, tool calls, state snapshots, activity records, diagnostics, and raw event timelines

Rationale: the purpose is to test Houmao's AG-UI protocol implementation. A direct client lets the workbench inspect exact event bytes and lifecycle behavior. CopilotKit can be added later as a comparison or renderer pane, but it should not hide protocol failures behind another runtime.

Alternative considered: build only a CopilotKit app with `HttpAgent`. That proves a common downstream integration path but is weaker for diagnosing `/connect`, multi-agent panes, raw events, and detach semantics.

### Keep an operator panel separate from agent panes

The operator input should be a pinned panel configured with one operator Houmao agent target. It submits prompts to that operator agent through AG-UI `/runs`. It should not broadcast user prompts to every pane and should not schedule other agents directly.

Rationale: the operator agent remains the coordination surface, while each pane remains a separate inspection and interaction surface for one running Houmao agent.

Alternative considered: make the operator input a global prompt fan-out control. That would turn the GUI into a scheduler and blur Houmao's existing coordination semantics.

### Use a local dev proxy with an allowlist

Browser requests should go through an app-local proxy by default. The proxy should forward HTTP and SSE requests to configured AG-UI targets, preserve response status and `text/event-stream` framing, abort upstream requests when the browser disconnects, and reject non-loopback targets unless explicitly allowed by configuration.

Rationale: this avoids requiring every per-agent gateway to expose permissive CORS while keeping remote target exposure controlled.

Alternative considered: require direct browser CORS to every gateway. That is simpler in the app but fragile for local sidecar ports and weakens the security boundary.

### Persist only UI configuration and layout

The app may persist pane layout, target labels, target URLs, selected thread IDs, and display preferences in browser local storage. It must not persist prompt text, streamed event payloads, credentials, headers, mailbox content, memory content, or raw terminal content by default.

Rationale: layout persistence is useful, but AG-UI events can contain sensitive task data.

Alternative considered: persist event history for debugging. That should remain an explicit export action if added later.

### Use Kimi Code headless for live validation

The required automated browser coverage should use a deterministic fake AG-UI server or Playwright route fixture. The live/manual validation path for this change should use a Kimi Code headless Houmao agent, targeting `kimi_headless` behavior through an already-running per-agent gateway. When the workspace has fixture credentials, prefer `tests/fixtures/auth-bundles/kimi/personal-a-default/` for the live check.

Rationale: the AG-UI workbench is meant to validate the high-fidelity headless stream path, and Kimi Code headless is the requested real-agent lane for this milestone. Keeping this separate from required fake-server E2E avoids making CI or ordinary implementation dependent on live model credentials.

Alternative considered: use Codex, Claude, or Gemini as the live validation lane. Those remain useful cross-checks, but this change should make Kimi Code headless the named manual lane.

## Risks / Trade-offs

- Target URL injection could turn the proxy into an SSRF helper. Mitigation: allow loopback targets by default, require explicit env configuration for remote hosts, reject unsupported protocols, and log the selected target without logging request bodies.
- Stream handling bugs could hide backend disconnect regressions. Mitigation: E2E tests should assert browser abort causes upstream abort or explicit detach and never maps to Houmao interrupt semantics.
- Dockview can add UI complexity. Mitigation: keep the first app shell narrow: pinned operator panel, add/remove panes, serialized docked layout, no custom drag behavior beyond Dockview defaults, and no floating or popout controls.
- Direct client code can drift from AG-UI TypeScript SDK behavior. Mitigation: import AG-UI types where practical, keep parsing and event reduction small, and include raw event inspection so drift is visible.
- Live Kimi Code credentials may be unavailable in developer workspaces. Mitigation: make deterministic fake AG-UI server tests the required browser coverage and document the Kimi Code headless live-agent check as opt-in evidence.

## Migration Plan

Create `apps/ag-ui-workbench/` without changing packaged Python code. Add documentation and scripts that run the app with Bun. Confirm Python distribution builds still include only `src/houmao` by relying on the existing wheel target and by avoiding any pyproject package include change.

Rollback is deleting the app directory and any app-level documentation entries. No runtime data migration is required.

## Open Questions

- Should the first implementation expose a CopilotKit comparison pane immediately, or should it wait until the direct client workbench is stable?
- Should pane configuration support custom headers in the first version, or should that wait until there is a clear authentication story for non-loopback AG-UI targets?
- Should exported event logs redact content automatically, or should event export remain out of scope for the first version?
