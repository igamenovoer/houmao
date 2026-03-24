## 1. Gateway and topology launch paths

- [ ] 1.1 Split gateway attach and lifecycle handling between same-session tmux auxiliary-window backends (`cao_rest`, tmux-backed headless) and detached backends (`houmao_server_rest`), including an explicit same-session gateway execution handle.
- [ ] 1.2 Implement same-session gateway auxiliary-window launch, readiness, liveness, and teardown using tmux pane metadata for local execution tracking and gateway health for readiness while keeping logs off the agent surface in window `0`.
- [ ] 1.3 Implement greenfield recovery work that preserves and restores the canonical agent surface in window `0` across gateway attach, detach, crash cleanup, and runtime relaunch flows.

## 2. Headless and CAO tmux surface control

- [ ] 2.1 Refactor headless tmux helpers so they keep window `0` named `agent` without forcing window `0` to be the selected foreground window, including separate behavior for creation-time selection versus pre-turn preparation.
- [ ] 2.2 Implement `cao_rest` window-topology normalization so the runtime prunes a distinct bootstrap window first, then moves the resolved CAO agent window into `:0`, while preserving CAO terminal identity semantics where possible and failing closed when normalization cannot safely establish window `0`.
- [ ] 2.3 Update runtime control and tmux-target resolution paths to follow the explicit agent surface instead of whichever tmux window is currently selected.

## 3. Observability, docs, and verification

- [ ] 3.1 Add one shared explicit agent-surface tmux resolver and update repo-owned tmux observers, demo helpers, and transport fallbacks that currently follow the session's active pane to use it.
- [ ] 3.2 Add unit and integration coverage for headless and `cao_rest` same-session auxiliary-window topologies, including prune-then-move CAO normalization, foreground auxiliary windows, repeated gateway attach or detach cycles, excluded `houmao_server_rest`, preserved window `0`, and relaunch-to-window-`0` behavior.
- [ ] 3.3 Update gateway, runtime, CAO, and troubleshooting docs to describe the new auxiliary-window contract and the intentionally non-contractual nature of non-zero tmux windows.
