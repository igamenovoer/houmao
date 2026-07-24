## ADDED Requirements

### Requirement: Provider restart readiness requires a fresh generation surface
For a tmux-backed tracked TUI, the tracking pipeline SHALL NOT apply prompt readiness parsed from a previous provider process to a newly observed provider process generation.

After a supported process changes from down to up or changes identity, the tracked state SHALL remain non-ready or unknown until current pane evidence proves that the new provider TUI has rendered its own current chrome and prompt after the latest shell boundary.

#### Scenario: New process before first render is not ready
- **WHEN** the previous provider process exited and a new supported provider process has started
- **AND WHEN** the pane still shows the prior TUI result and the shell launch command without a fresh new-provider prompt
- **THEN** live tracked state does not publish `surface.ready_posture=yes` from the stale prior surface

#### Scenario: Fresh provider prompt opens readiness
- **WHEN** the new process generation renders fresh provider chrome and a current empty prompt after the latest shell boundary
- **THEN** ordinary detector and stability rules may publish ready posture for that generation
