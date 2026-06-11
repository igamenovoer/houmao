## Context

The AG-UI workbench has editable text areas that submit text through explicit buttons: normal agent panes use a prompt composer with a Run button, and Debug Agent panes use an editor with a Send button. These surfaces already have guarded send functions that ignore empty content and dispatch the correct runtime or debug-publish workflow.

The requested change is a keyboard affordance across these send-capable editors. It should not alter AG-UI request construction, target state, runtime ownership, persistence, validation, or button behavior.

## Goals / Non-Goals

**Goals:**

- Add `Shift+Enter` submission to every workbench text editor whose primary purpose is editing text that can be sent from the same pane.
- Preserve button submission as the same source of truth for validation and dispatch behavior.
- Preserve multiline editing by keeping plain `Enter` as text insertion in textarea-based prompt editors.
- Cover the behavior with deterministic browser tests for normal agent prompt submission and Debug Agent editor submission.

**Non-Goals:**

- No global document-level keyboard shortcut.
- No changes to AG-UI request bodies, debug publish payloads, active-thread behavior, or tmux terminal input.
- No change to read-only text areas such as generated curl output.
- No introduction of a new keyboard shortcut settings system.

## Decisions

Use local textarea `onKeyDown` handlers for send-capable editors.

Rationale: each editor already owns its send function and empty-content guard, so a local handler can call the same function used by the button. This avoids a global keyboard listener that could accidentally submit while focus is in target forms, tmux terminals, dropdown filters, or read-only output fields.

Alternative considered: a shared document listener that checks the active element. This is broader than needed and creates a higher risk of submitting the wrong pane.

Keep send behavior centralized in existing send/run functions.

Rationale: the shortcut should behave exactly like clicking Run or Send, including whitespace trimming, validation, runtime dispatch, and publish response handling. The handler should only detect the key gesture, prevent textarea newline insertion for the submit gesture, and call the existing function.

Alternative considered: duplicate submit logic inside each key handler. That would risk divergent empty-state and validation behavior over time.

Use a small reusable helper only if two or more editors need the same handler shape.

Rationale: the initial scope has at least two textarea send surfaces. A helper such as `submitOnShiftEnter(event, submit)` can keep the shortcut definition consistent while staying simple. If implementation reads cleaner with inline handlers, that is acceptable as long as tests cover both panes.

## Risks / Trade-offs

- Shortcut expectation conflict: some users may expect `Shift+Enter` to insert a newline. Mitigation: the user explicitly requested `Shift+Enter` to send; preserve plain `Enter` for newlines.
- Accidental duplicate sends from key repeat: repeated keydown events may trigger multiple sends if the user holds the keys. Mitigation: ignore `event.repeat` for submit shortcuts or rely on existing request-state guards if present.
- Hidden send surfaces missed during implementation: future panes may add text send editors. Mitigation: tests should cover current agent and debug surfaces, and implementation should document or centralize the helper so future editors can opt in.
