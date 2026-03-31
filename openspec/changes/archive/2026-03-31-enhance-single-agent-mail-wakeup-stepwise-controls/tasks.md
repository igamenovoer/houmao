## 1. Stepwise Gateway Mode

- [x] 1.1 Update the stepwise `start` path to attach the gateway in a foreground auxiliary tmux window while keeping `auto` and `matrix` on the existing detached gateway path.
- [x] 1.2 Persist and expose the stepwise gateway watchability metadata needed for later `attach` and `watch-gateway` commands without relying on manual tmux window discovery.

## 2. Operator Command Surface

- [x] 2.1 Extend the demo command parser and runner with `attach`, `send`, and `watch-gateway`, keeping `manual-send` only as an optional compatibility alias.
- [x] 2.2 Implement `watch-gateway` by resolving the authoritative gateway tmux window from live status and printing its console output via `tmux capture-pane`, including a follow/polling mode and clear inactive-session failures.
- [x] 2.3 Add a grouped `notifier` command surface with `status`, `on`, `off`, and `set-interval`, reusing the existing gateway mail-notifier lifecycle operations for the active demo instance.

## 3. Docs and Verification

- [x] 3.1 Update the demo README and operator guidance to teach the stepwise flow as `start -> attach -> watch-gateway -> send -> verify -> stop`, including notifier control examples.
- [x] 3.2 Extend focused demo unit coverage for the expanded command surface, stepwise foreground gateway behavior, and notifier command handling.
- [x] 3.3 Re-run focused demo verification, including `auto --tool claude` and `auto --tool codex`, to confirm the new stepwise controls do not regress the canonical automatic workflow.
