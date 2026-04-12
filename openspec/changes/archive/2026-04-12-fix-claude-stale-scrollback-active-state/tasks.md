## 1. Regression Coverage

- [x] 1.1 Add a Claude stale-scrollback fixture or synthetic surface based on the upstream capture shape: historical thinking/progress rows, a later `Worked for ...` completion marker, and a final empty prompt.
- [x] 1.2 Add detector-level coverage in `tests/unit/shared_tui_tracking/test_claude_code_session.py` proving historical thinking/spinner rows above the current turn region do not produce `active_evidence` or `thinking_line` for a submit-ready prompt.
- [x] 1.3 Add session-level coverage proving the same full-scrollback surface publishes `surface_ready_posture=yes` and `turn_phase=ready`.
- [x] 1.4 Add or preserve a current-active Claude case proving thinking/spinner/tool activity inside the current turn region still produces active evidence.

## 2. Claude Detector Implementation

- [x] 2.1 Add a Claude latest-turn activity-region helper in `src/houmao/shared_tui_tracking/apps/claude_code/profile.py` using the existing latest prompt-anchor boundary behavior.
- [x] 2.2 Scope thinking, spinner, active block, and tool-activity scans to the current latest-turn activity region before adding active reasons.
- [x] 2.3 Keep interruptable footer handling conservative so a current interruptable footer can still make the turn active or unknown, while stale scrollback rows alone cannot.
- [x] 2.4 Ensure completion-marker and response-candidate handling still recognizes current completed Claude turns without reviving historical activity evidence.

## 3. Validation

- [x] 3.1 Run the targeted shared TUI tracking tests for Claude detector/session behavior.
- [x] 3.2 Run the relevant broader unit test command, or document why only targeted tests were run.
- [x] 3.3 Run OpenSpec validation/status for `fix-claude-stale-scrollback-active-state` and confirm the change is ready for apply.
