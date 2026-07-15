## ADDED Requirements

### Requirement: Current Codex and Kimi validation uses high-rate truth and varied sparse replay
Recorded validation for Codex 0.144.x and Kimi 0.23.x SHALL capture unattended live TUI sessions at about 20 frames per second. Maintainers SHALL manually label the high-rate source timeline before using tracker output as an oracle.

Validation SHALL derive multiple lower-rate streams or delay schedules from the same source recording, including regular and jittered sampling. Strict comparisons MAY allow skipped transient labels, but every replay SHALL preserve meaningful state ordering, avoid false operator-blocked prompts in unattended mode, and avoid impossible terminal-to-active transitions caused only by capture delay.

#### Scenario: One source recording drives several delay simulations
- **WHEN** a maintainer validates a current Codex or Kimi TUI scenario
- **THEN** the workflow replays the manually labeled 20 fps source and multiple lower-rate or jittered derivatives
- **AND THEN** every derived sample remains traceable to its source sample

#### Scenario: Sparse replay is judged semantically
- **WHEN** a sparse replay misses a short manually labeled transition
- **THEN** validation may accept a different sample-aligned label sequence
- **AND THEN** it still rejects sequences that falsely report readiness, operator confirmation, or terminal success while later evidence shows the same turn active

