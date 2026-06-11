## Why

Prompt editors in the AG-UI workbench currently rely on button clicks for submission, which slows repeated prompt/send workflows across agent and debug panes. The workbench should support a consistent keyboard submit gesture in every editable prompt/composer area that sends text.

## What Changes

- Add a keyboard submission shortcut for every prompt/composer text area that sends editable text in `apps/ag-ui-workbench`.
- Use `Shift+Enter` to send the current prompt from those editors.
- Preserve existing button-based send/run behavior.
- Preserve normal text editing behavior for non-submit keys, including plain `Enter` for inserting a newline unless an existing editor intentionally owns a different behavior.
- Prevent empty or whitespace-only prompt submissions from the shortcut, matching existing send/run guards.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ag-ui-workbench-app`: Agent and debug prompt/composer editors gain a consistent `Shift+Enter` keyboard shortcut for sending text.

## Impact

- Affected app code: prompt/composer text areas and send/run handlers under `apps/ag-ui-workbench/src/`.
- Affected tests: workbench browser coverage for agent pane prompt submission and any debug/composer text send surfaces.
- No AG-UI protocol, backend, storage, or dependency changes are expected.
