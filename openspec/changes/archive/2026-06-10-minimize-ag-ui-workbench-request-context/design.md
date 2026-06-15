## Context

The workbench currently builds `RunAgentInput` with `state.houmaoWorkbench` and non-Houmao `forwardedProps` containing source, pane id, and pane kind. The gateway prompt converter includes non-empty `state` in the agent prompt and filters unrecognized `forwardedProps` into an omitted-key diagnostic, so those fields cost tokens without helping graphics authoring.

The `houmao-agent-ag-ui` system skill already owns the static authoring knowledge: component names, schema discovery, payload validation, event rendering, publish commands, live-only delivery semantics, and safety rules. The GUI should only send dynamic information the skill cannot know, primarily the current display area available for a graphic.

## Goals / Non-Goals

**Goals:**

- Keep normal workbench AG-UI run requests small and protocol-conforming.
- Provide a compact canvas-size hint for agents that create graphics.
- Avoid duplicating AG-UI authoring instructions already present in `houmao-agent-ag-ui`.
- Avoid putting redundant pane/source metadata into fields that become agent-visible prompt context.

**Non-Goals:**

- Do not change gateway AG-UI route validation or publish semantics.
- Do not add gateway validation for Houmao component schemas.
- Do not introduce frontend tool execution through `RunAgentInput.tools`.
- Do not add a durable server-side cache of GUI presentation context.

## Decisions

### Use `context` only for dynamic canvas size

Normal workbench run submissions should include at most one Houmao canvas context entry:

```json
{
  "description": "houmao.canvas_size_px.v1",
  "value": "{\"widthPx\":640,\"heightPx\":520}"
}
```

AG-UI `Context.value` is a string in the SDK schema, so the canvas object is encoded as a compact JSON string. `widthPx` and `heightPx` are rounded positive CSS pixel dimensions of the display surface that will render graphics. The description includes `canvas_size_px` so the field is recognizable in the agent prompt without additional explanatory text.

Alternative considered: include renderer profile, component lists, command recipes, delivery semantics, `threadId`, `devicePixelRatio`, and safety rules. That duplicates the system skill or existing structured AG-UI fields, so it is rejected for the normal path.

### Send empty `state` and empty ordinary `forwardedProps`

For ordinary workbench prompt submission, `state` should be `{}` and `forwardedProps` should be `{}`. Pane id, pane kind, and source name are useful for browser diagnostics but not for the managed agent. If a future request needs gateway-recognized runtime controls, those controls can still use the existing `forwardedProps.houmao.chatSession` and `forwardedProps.houmao.execution` allowlist.

Alternative considered: keep pane metadata in `state` as provenance. The gateway renders `state` into the prompt, so this would keep paying a token cost for data the agent does not need.

### Keep `tools` empty for typed graphics

Houmao typed components are output payloads carried by standard AG-UI tool-call events. They are not client-executable frontend tools. Workbench run submissions should continue to send `tools: []` unless a later feature implements actual frontend tool execution.

Alternative considered: advertise `houmao.chart.*` components as tools. That would misrepresent the protocol and could make agents attempt a frontend-tool workflow the GUI does not support.

### Apply the trim to connect requests too, without canvas context

Connect requests do not submit work to the agent, so they should not need canvas context. They should still stop sending pane/source metadata through `state` or non-Houmao `forwardedProps` because the gateway does not use it for connection routing.

## Risks / Trade-offs

- Agents lose pane id/kind in prompt context -> Mitigation: those values are not needed for graphics routing; `threadId` and `runId` already appear in the gateway's structured AG-UI context.
- Canvas measurement can be unavailable during early render -> Mitigation: omit the canvas context rather than guessing dimensions.
- Very small context gives less renderer detail -> Mitigation: rely on `houmao-agent-ag-ui` for static renderer and schema knowledge, and add fields later only when a concrete workflow needs them.
