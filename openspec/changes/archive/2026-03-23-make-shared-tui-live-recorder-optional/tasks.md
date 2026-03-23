## 1. Config And CLI Contract

- [x] 1.1 Add a demo-config field for live-watch recorder enablement with a checked-in default of disabled, and regenerate the packaged schema if needed.
- [x] 1.2 Thread the live-watch recorder toggle through config resolution, boundary models, and the `start` command so operators can explicitly enable recorder capture for one run.
- [x] 1.3 Update persisted live-watch manifest and inspect payload shapes so recorder enablement and recorder-root presence are explicit instead of assumed.

## 2. Live-Watch Runtime Behavior

- [x] 2.1 Refactor live-watch startup so default runs skip terminal-recorder and recorder-enabled runs keep the existing passive-recorder path.
- [x] 2.2 Update the dashboard reduction loop to consume direct visible-pane tmux captures when recorder is disabled and recorder pane snapshots when recorder is enabled.
- [x] 2.3 Make stop/finalization conditional so recorder-disabled runs still emit live-state reports while recorder-enabled runs retain replay/comparison behavior.
- [x] 2.4 Preserve best-effort compatibility for older recorder-backed live-watch manifests when inspecting or stopping existing runs.

## 3. Verification And Docs

- [x] 3.1 Update shared-TUI demo docs and config reference text to describe recorder-default-off live watch and explicit replay-debug enablement.
- [x] 3.2 Refresh or add unit tests for config parsing, start/inspect/stop behavior, and dashboard/live-state handling in both recorder-disabled and recorder-enabled modes.
- [x] 3.3 Run the focused shared-TUI demo and config test suites that cover the new live-watch behavior.
