## ADDED Requirements

### Requirement: Operator-facing tmux handoff is interactivity-aware and libtmux-backed
When repo-owned Houmao code needs to hand an operator terminal off to a tmux session after a successful managed launch, it SHALL resolve the session through the repo-owned libtmux-backed tmux integration layer rather than composing an ad hoc raw `tmux attach-session` subprocess call.

If libtmux does not expose a first-class attach helper for the needed session handoff, the implementation SHALL use libtmux-owned command dispatch bound to the resolved tmux server or session object rather than introducing a separate unrelated raw tmux subprocess path.

Before attempting tmux attach, the handoff flow SHALL determine whether the caller provides a usable interactive terminal. When the caller is non-interactive, the handoff flow SHALL skip the attach attempt and return or report tmux session coordinates for manual follow-up instead of surfacing raw tmux `not a terminal` output as a launch failure.

#### Scenario: Interactive caller uses libtmux-backed session handoff
- **WHEN** a repo-owned managed launch flow needs to attach an interactive caller to tmux session `S`
- **AND WHEN** the caller provides a usable interactive terminal
- **THEN** the flow resolves session `S` through the repo-owned libtmux integration layer
- **AND THEN** any resulting attach command is issued through libtmux-owned command dispatch rather than through an unrelated raw tmux subprocess helper

#### Scenario: Non-interactive caller skips attach and reports follow-up coordinates
- **WHEN** a repo-owned managed launch flow finishes starting tmux session `S`
- **AND WHEN** the caller does not provide a usable interactive terminal
- **THEN** the flow does not attempt a tmux attach that would fail only because the caller is non-interactive
- **AND THEN** it reports the tmux session coordinates needed for a later manual attach
