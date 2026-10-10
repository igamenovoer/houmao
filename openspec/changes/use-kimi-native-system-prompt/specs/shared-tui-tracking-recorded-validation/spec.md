## MODIFIED Requirements

### Requirement: Current Codex and Kimi validation uses high-rate truth and varied sparse replay
Recorded validation for Codex 0.144.x and the Kimi 0.34.x baseline SHALL capture unattended live TUI sessions at about 20 frames per second. Maintainers SHALL manually label the high-rate source timeline before using tracker output as an oracle. The Kimi baseline evidence SHALL support the maintained `>=0.34.0` profile without imposing an upper version limit.

Validation SHALL derive multiple lower-rate streams or delay schedules from the same source recording, including regular and jittered sampling. Strict comparisons MAY allow skipped transient labels, but every replay SHALL preserve meaningful state ordering, avoid false operator-blocked prompts in unattended mode, and avoid impossible terminal-to-active transitions caused only by capture delay.

Kimi validation SHALL record that native role-prompt projection completed before TUI startup and SHALL contain no role-bootstrap chat turn. Recordings from pre-0.34 Kimi releases SHALL NOT qualify maintained Kimi behavior.

#### Scenario: One source recording drives several delay simulations
- **WHEN** a maintainer validates a current Codex or Kimi TUI scenario
- **THEN** the workflow replays the manually labeled 20 fps source and multiple lower-rate or jittered derivatives
- **AND THEN** every derived sample remains traceable to its source sample

#### Scenario: Sparse replay is judged semantically
- **WHEN** a sparse replay misses a short manually labeled transition
- **THEN** validation may accept a different sample-aligned label sequence
- **AND THEN** it still rejects sequences that falsely report readiness, operator confirmation, or terminal success while later evidence shows the same turn active

#### Scenario: Kimi qualification uses the maintained version and prompt path
- **WHEN** a Kimi recording is used to qualify the maintained tracker profile
- **THEN** its metadata identifies the Kimi 0.34.x baseline and native pre-start role-prompt projection
- **AND THEN** it contains neither a pre-0.34 compatibility claim nor a role-bootstrap chat turn
