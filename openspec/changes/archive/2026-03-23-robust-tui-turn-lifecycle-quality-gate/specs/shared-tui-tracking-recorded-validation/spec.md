## ADDED Requirements

### Requirement: Recorded validation SHALL keep complex multi-turn regression fixtures as a maintained quality gate
The recorded validation workflow SHALL keep a maintained complex recorded interaction fixture for Claude and a parallel maintained complex recorded interaction fixture for Codex in the committed corpus under `tests/fixtures/shared_tui_tracking/recorded/`.

Each complex fixture SHALL be sourced from a real tmux-backed capture authored through the recorded-validation workflow and SHALL exercise the lifecycle:

- short prompt -> settled success,
- long prompt with a ready-draft span before submit,
- active turn with a visible active-draft span while the turn is still in flight,
- intentional interrupt to interrupted-ready,
- another prompt with another ready-draft span before submit,
- another active turn with another active-draft span,
- second intentional interrupt to interrupted-ready, and
- final short prompt -> settled success.

The maintained replay-validation suite SHALL continue to run those fixtures so they remain a standing regression gate rather than one-off authoring artifacts.
When tracker lifecycle semantics change in ways that can shift public-state labels, the maintained validation workflow SHALL revalidate any previously committed affected fixtures before the maintained corpus is treated as passing again.

#### Scenario: Maintained validation suite runs the complex regression fixtures
- **WHEN** a developer runs the maintained recorded-validation regression suite
- **THEN** the suite includes the canonical Claude and Codex complex interaction fixtures
- **AND THEN** those fixtures continue to serve as a standing quality gate for repeated interruption, overlapping draft editing, and terminal-result reset behavior

#### Scenario: Lifecycle-semantic changes force affected fixture revalidation
- **WHEN** the tracker changes turn-lifecycle semantics in a way that can shift replay labels for previously committed recorded fixtures
- **THEN** the maintained validation workflow replays those affected fixtures again
- **AND THEN** the maintained corpus is not treated as green until any changed labels are revalidated or updated explicitly

### Requirement: Recorded validation SHALL judge complex success-interrupt-success lifecycles against public tracked state
For the maintained complex fixtures, the replay comparison contract SHALL make it possible to judge:

- first settled-success posture,
- reset of `last_turn.result` and `last_turn.source` during both ready-draft spans,
- `surface.editing_input=yes` during both active-draft spans,
- first interrupted-ready posture,
- second interrupted-ready posture, and
- final settled-success posture without carrying interrupted state into the last turn.

The maintained cadence-sweep contract for these fixtures SHALL be able to require an ordered repeated transition sequence equivalent to `ready_success -> active -> ready_interrupted -> active -> ready_interrupted -> ready_success`.
That cadence-sweep contract SHALL remain a coarse transition gate; ready-draft and active-draft semantics SHALL continue to be judged by sample-aligned ground truth rather than by adding new sweep-only draft labels.

#### Scenario: Complex fixture replay detects stale last-turn carry or draft-editing regressions
- **WHEN** a developer replays one maintained complex success-interrupt-success fixture through recorded validation
- **THEN** the resulting replay and ground-truth comparison can detect whether interrupted state leaked into a later draft or active span
- **AND THEN** the comparison can detect whether overlapping active drafting failed to report `surface.editing_input=yes`
- **AND THEN** the ordered sweep contract can detect whether one of the repeated active or interrupted phases collapsed out of the lifecycle

#### Scenario: Draft semantics remain in the strict ground-truth path
- **WHEN** one maintained complex fixture includes ready-draft and active-draft spans
- **THEN** those draft-specific semantics are judged through the sample-aligned replay-versus-ground-truth comparison
- **AND THEN** the sweep contract is not required to introduce additional draft-only state labels to validate that fixture
