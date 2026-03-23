## 1. Runtime Session Shape

- [x] 1.1 Update tmux-backed headless session bootstrap so window 0 is reserved, selected, and named `agent` as the stable primary surface.
- [x] 1.2 Replace per-turn `tmux new-window` execution with same-pane fresh-process reuse of the `agent` window, preserving per-turn stdout, stderr, exitcode, process metadata, rolling pane output, and return to an idle shell after each turn.
- [x] 1.3 Remove runtime assumptions that turn identity is encoded in tmux window names, replace `new-window -P`-derived targeting with a stable window-0 reference, and keep one live runtime-controlled execution at a time per headless session.

## 2. Managed Headless Control

- [x] 2.1 Replace server-side managed-headless `kill-window` interrupt fallback with process-signal-first control that only falls back to control input aimed at the stable `agent` window in slot 0.
- [x] 2.2 Replace runner-side `kill-window` interrupt and terminate fallbacks with stable-surface control that preserves the headless session and its primary window.
- [x] 2.3 Repurpose managed-headless `tmux_window_name` and related inspectability guidance to the stable value `agent`, and ensure auxiliary windows used for gateway, logs, or diagnostics remain non-authoritative.

## 3. Verification

- [x] 3.1 Add focused runtime tests proving headless sessions keep the agent in window 0, name it `agent`, reuse the same primary surface across turns, and do not create per-turn windows during normal turn execution.
- [x] 3.2 Add managed-headless server tests covering stable-surface interrupt/control behavior, `tmux_window_name="agent"` metadata, auxiliary-window tolerance, and continued single-active-turn enforcement.
- [x] 3.3 Re-run `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/run-case.sh` for the canonical unattended case and verify that attach/capture guidance points to the stable `agent` window while preserving rolling output.
