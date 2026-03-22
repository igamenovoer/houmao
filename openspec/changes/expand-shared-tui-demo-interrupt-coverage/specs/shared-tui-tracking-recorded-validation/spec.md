## ADDED Requirements

### Requirement: Recorded validation SHALL support semantic scenario intents for intentional interrupt and intentional close
The recorded validation workflow SHALL support intent-level scenario actions for intentional interrupt and intentional close in addition to raw low-level input actions.

The intent-level actions SHALL allow the workflow to express operator meaning without requiring every supported tool to share the same literal key sequence or close recipe.

#### Scenario: Harness executes a repeated-interruption scenario through tool-specific intents
- **WHEN** a maintainer runs a recorded-capture scenario that includes intentional interruption and final close
- **THEN** the scenario can express interruption and close as semantic operator intents
- **AND THEN** the workflow resolves those intents through the selected tool’s supported recipe rather than assuming one literal low-level key path for every tool

### Requirement: Recorded validation SHALL judge repeated interrupted-turn lifecycles against public tracked state
The recorded validation workflow SHALL support canonical fixtures that exercise a repeated interrupted-turn lifecycle of `prompt -> active -> interrupt -> prompt -> interrupt -> close`.

For such fixtures, the comparison contract SHALL make it possible to judge:

- first interrupted-ready posture,
- reset of `last_turn_result` when the second turn becomes active,
- second interrupted-ready posture, and
- final diagnostics-loss posture after close without inventing a terminal success or known failure.

#### Scenario: Repeated interruption fixture is replayed against ground truth
- **WHEN** a developer replays a repeated intentional-interruption fixture through recorded validation
- **THEN** the resulting replay and ground-truth comparison can distinguish both interrupted turn cycles
- **AND THEN** the comparison can detect whether interruption state was incorrectly carried into the second active turn
- **AND THEN** the comparison can detect whether close produced an incorrect terminal result

## MODIFIED Requirements

### Requirement: Recorded validation SHALL support config-defined capture-frequency robustness sweeps
The recorded validation workflow SHALL support named sweep definitions from the demo-owned configuration that vary evidence cadence for the same scenario or fixture workflow.

Sweep verdicts SHALL be based on transition-contract expectations rather than on blindly reusing a canonical sample-aligned ground-truth timeline across all cadences.

When a sweep covers a lifecycle that intentionally repeats the same transition family more than once, the configured transition contract SHALL be able to express repeated or ordered occurrence expectations rather than only first-occurrence label presence.

#### Scenario: Recorded validation executes a frequency sweep from config
- **WHEN** a developer runs a config-defined capture-frequency sweep
- **THEN** the workflow executes each configured cadence variant
- **AND THEN** the resulting verdicts explain whether required tracker transitions and terminal outcomes remained observable at each cadence
- **AND THEN** repeated-transition cases can require an ordered or repeated transition family rather than collapsing to one first occurrence

### Requirement: Recorded validation SHALL ship an initial multi-tool fixture corpus for critical state transitions
The repository SHALL include an initial recorded fixture corpus for the standalone shared TUI tracker, and the canonical committed version of that corpus SHALL be sourced from real tmux-backed captures authored with the recorded-validation workflow rather than from synthetic hand-authored recorder payloads.

At minimum, the first-wave canonical corpus SHALL contain:

- Claude `explicit_success`
- Claude `interrupted_after_active`
- Claude `double_interrupt_then_close`
- Claude `slash_menu_recovery`
- Claude `tui_down_after_active`
- Codex `explicit_success`
- Codex `interrupted_after_active`
- Codex `double_interrupt_then_close`
- Codex `tui_down_after_active`

Each published canonical fixture SHALL preserve the replay-grade canonical artifact set for that case, including the fixture manifest, pane snapshots, runtime observations, labels, and authoritative input events when present.

#### Scenario: Maintained recorded-validation suite runs against the real first-wave corpus
- **WHEN** a developer runs the maintained recorded-validation test suite
- **THEN** the suite includes a canonical first-wave fixture set spanning both Claude and Codex from real tmux-backed captures
- **AND THEN** that corpus exercises success, interruption, repeated intentional interruption with close, ambiguity, and diagnostics-loss boundaries for the standalone tracker
