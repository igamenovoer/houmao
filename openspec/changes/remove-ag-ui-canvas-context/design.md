## Context

The AG-UI workbench currently measures the agent pane display surface on prompt submission and passes that measurement through the runtime action into the AG-UI request builder. The builder converts the measurement into a `RunAgentInput.context` entry named `houmao.canvas_size_px.v1`.

That context is agent-visible. It appears in the gateway's prompt rendering as an AG-UI context entry, where the agent can treat it as a fixed target size. The value is only a momentary GUI measurement, so it can become stale after pane resizing, scroll changes, renderer selection, transcript growth, or other interaction.

## Goals / Non-Goals

**Goals:**

- Remove all GUI-derived canvas-size context from normal agent pane prompt runs.
- Keep AG-UI run request bodies deterministic and metadata-minimal.
- Keep the implementation local to the workbench request path and tests.
- Preserve the gateway's ability to render context entries when another caller intentionally supplies them.

**Non-Goals:**

- Redesign responsive chart sizing or renderer layout.
- Add a replacement canvas sizing protocol.
- Remove AG-UI `context` from the protocol or backend models.
- Change connect/watch request behavior, which already uses empty context.

## Decisions

1. Normal workbench prompt runs will always send `context: []`.

   The simplest and most predictable contract is that the workbench does not send volatile layout measurements at all. Responsive rendering should be handled by the GUI renderer and graphic payload rules, not by asking the agent to target a transient pane measurement. The main alternative was to send a broader layout contract, but that would still be stale after user interaction and would keep misleading prompt context in the agent loop.

2. Remove `canvasSize` from the workbench run action path.

   The pane should not measure the display surface during prompt submission, and the runtime action should not carry a field that no longer affects request construction. Keeping the field but ignoring it would leave a misleading API surface and allow future call sites to reintroduce the behavior accidentally.

3. Keep `context` present as an empty array in `RunAgentInput`.

   The existing workbench request shape uses explicit empty arrays and objects for optional protocol sections. Keeping `context: []` preserves the metadata-minimal shape and makes tests assert the absence of GUI context directly.

4. Do not change backend prompt rendering.

   The backend still needs to display context entries supplied by non-workbench callers. This change removes the workbench source of `houmao.canvas_size_px.v1`; it does not redefine AG-UI context semantics globally.

## Risks / Trade-offs

- Agents that used `houmao.canvas_size_px.v1` lose that hint -> Update guidance and tests to prefer responsive graphics and explicit user-provided sizing when needed.
- Hidden test fixtures may still expect the old context entry -> Search for `houmao.canvas_size_px.v1`, `canvasSize`, and related body assertions during implementation.
- Future callers may need stable sizing constraints -> Add a separate, intentional sizing contract later instead of reusing pane measurements.

## Migration Plan

1. Update the workbench run action type and dispatch sites to remove `canvasSize`.
2. Update `buildRunInput` so prompt runs set `context: []` directly and remove the canvas context helper if unused.
3. Update Playwright/runtime tests and docs to assert that prompt runs carry no GUI layout context.
4. Run the workbench test suite and targeted type checks.

Rollback is straightforward: reintroduce the `canvasSize` action field and `canvasContext` helper, then restore the previous request body assertions.

## Open Questions

None.
