## 1. Claude Activity Detection

- [x] 1.1 Remove fixed thinking and tool-activity phrase lists from Claude active-turn evidence.
- [x] 1.2 Preserve current structural active evidence from spinner-glyph rows, interruptable footer posture, and current active block shape.
- [x] 1.3 Ensure stale or incidental prose-only thinking/tool text cannot downgrade an otherwise submit-ready Claude prompt to active.

## 2. Regression Coverage

- [x] 2.1 Add Claude detector coverage for a prompt-ready surface containing stale or incidental thinking/tool prose without current structural active evidence.
- [x] 2.2 Add Claude detector coverage proving a current spinner-glyph row still reports active-turn evidence.
- [x] 2.3 Add session-level coverage verifying the prose-only prompt-ready case keeps `surface_ready_posture=yes` and `turn_phase=ready`.

## 3. Verification

- [x] 3.1 Run the focused Claude shared TUI tracking tests.
- [x] 3.2 Run OpenSpec validation/status for `use-spinner-for-claude-activity-detection` and confirm the change is apply-ready.
