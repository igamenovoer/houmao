## Why

Claude Code can render an auto-suggestion on the prompt line in a darker style than ordinary typed prompt text. The current tracked-TUI readiness path can treat that visible suggestion as editable draft input, which makes the gateway mail notifier defer even though the operator has not typed anything.

## What Changes

- Update Claude prompt-area signal classification so darker styled auto-suggestion text is treated as placeholder or suggestion content, not user-authored draft input.
- Base that classification on raw terminal styling and prompt-region structure, not on exact suggestion text such as `check mail`.
- Preserve the existing safety rule that real typed draft input remains `surface.editing_input=yes` and blocks notifier prompt injection.
- Ensure gateway notifier readiness behavior benefits from the corrected tracked state without adding notifier-side text heuristics.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `versioned-tui-signal-profiles`: Claude prompt behavior variants must distinguish darker styled ghost-suggestion payloads from real drafts using rendering/style evidence rather than exact text.
- `official-tui-state-tracking`: Live tracked state must report styled Claude suggestion payloads as non-editing ready posture while preserving real draft editing semantics.
- `agent-gateway-mail-notifier`: Gateway notifier prompt-readiness gating must allow notification when the TUI is otherwise ready and the only prompt payload is a style-classified suggestion.

## Impact

- Affected code: Claude prompt behavior classification in `src/houmao/shared_tui_tracking/apps/claude_code/signals/prompt_behavior.py`, Claude tracked signal projection in `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`, and related tests under `tests/unit/shared_tui_tracking/` and `tests/unit/explore/`.
- Affected runtime behavior: TUI-backed gateway mail notifier prompts can enqueue when Claude shows a non-editable auto-suggestion on an otherwise ready prompt.
- No API, CLI, dependency, or storage format changes are expected.
