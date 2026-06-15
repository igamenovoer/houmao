## Why

The AG-UI workbench currently sends GUI provenance fields in `forwardedProps` and no useful canvas hint in `context`, which adds prompt noise without helping agents craft graphics. Agents already use the `houmao-agent-ag-ui` skill for component schemas, validation, rendering, publishing, and safety guidance, so the GUI request should only provide dynamic presentation facts the skill cannot know.

## What Changes

- Make workbench-submitted AG-UI run inputs use an empty `forwardedProps` object unless a gateway-recognized Houmao runtime control is explicitly needed.
- Add a compact AG-UI context entry for the visible canvas size, using `description: "houmao.canvas_size_px.v1"` and a JSON-string `value` such as `{"widthPx":640,"heightPx":520}`.
- Keep pane identity, source labels, component lists, CLI recipes, delivery semantics, and safety rules out of the agent-visible run request.
- Keep `tools` empty for normal workbench submissions because Houmao graphics components are output payloads, not client-executable frontend tools.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ag-ui-workbench-app`: tighten the AG-UI run request contract so the workbench sends only minimal dynamic canvas context and does not expose redundant pane/source metadata through `forwardedProps`.

## Impact

- Affected code is primarily the AG-UI workbench request construction in `apps/ag-ui-workbench/src/ag-ui/client.ts` and callers that can measure the display surface before submitting a run.
- Browser tests should assert that submitted run inputs omit unnecessary forwarded props and include only the compact canvas context when dimensions are available.
- Gateway behavior does not need to change; it already renders `RunAgentInput.context` into the prompt and ignores empty `forwardedProps`.
