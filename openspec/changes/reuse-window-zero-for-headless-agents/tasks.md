## 1. Runtime Session Shape

- [ ] 1.1 Update tmux-backed headless session bootstrap so window 0 is reserved and named as the stable primary agent surface.
- [ ] 1.2 Replace per-turn `tmux new-window` execution with window-0 command injection that preserves per-turn stdout, stderr, exitcode, process metadata, and rolling pane output.
- [ ] 1.3 Remove runtime assumptions that turn identity is encoded in tmux window names and keep one live runtime-controlled execution at a time per headless session.

## 2. Managed Headless Control

- [ ] 2.1 Update managed-headless active-turn metadata and fallback interrupt/control paths to target the stable primary agent surface instead of `turn-N` windows.
- [ ] 2.2 Update managed-agent detailed-state and related inspectability surfaces so tmux guidance anchors to window 0 and ignores auxiliary windows for turn truth.
- [ ] 2.3 Ensure auxiliary windows used for gateway, logs, or diagnostics remain non-authoritative and do not redefine the headless agent surface.

## 3. Verification

- [ ] 3.1 Add focused runtime tests proving headless sessions keep the agent in window 0 and do not create per-turn windows during normal turn execution.
- [ ] 3.2 Add managed-headless server tests covering stable-surface interrupt/control behavior and continued single-active-turn enforcement.
- [ ] 3.3 Re-run the headless demo or autotest harness and verify that attach/capture guidance points to the stable window-0 agent surface while preserving rolling output.
