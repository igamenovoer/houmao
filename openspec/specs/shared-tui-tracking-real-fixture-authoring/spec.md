# shared-tui-tracking-real-fixture-authoring Specification

## Purpose
Define the maintainer workflow for authoring, validating, reviewing, and promoting real tmux-backed fixtures for the shared tracked-TUI demo pack.
## Requirements
### Requirement: Maintainers SHALL author real shared-tracker fixtures from temporary tmux capture runs before promotion
Maintainers SHALL author real shared-tracker fixtures under a temporary subtree such as `tmp/demo/shared-tui-tracking-demo-pack/authoring/` before promoting any artifact set into `tests/fixtures/shared_tui_tracking/recorded/`.

The workflow SHALL use the demo pack’s live watch, recorded capture, recorded validation, and review-video steps rather than a parallel ad hoc recording path.

#### Scenario: Maintainer authors a fixture in temporary space before promotion
- **WHEN** a maintainer prepares a new or replacement real fixture for the shared tracked-TUI corpus
- **THEN** the capture and labeling work is first performed under `tmp/demo/shared-tui-tracking-demo-pack/authoring/`
- **AND THEN** promotion into the committed fixture tree happens only after the temporary authoring run has passed the documented validation gates

### Requirement: The repository SHALL maintain a first-wave real capture matrix with concrete prompts and target transitions
The repository SHALL maintain a first-wave real fixture matrix spanning Claude and Codex with concrete prompts, operator actions, and expected transition families so authoring remains reproducible.

At minimum, that first-wave matrix SHALL include:

- Claude `explicit_success`
- Claude `interrupted_after_active`
- Claude `double_interrupt_then_close`
- Claude `slash_menu_recovery`
- Claude `tui_down_after_active`
- Codex `explicit_success`
- Codex `interrupted_after_active`
- Codex `double_interrupt_then_close`
- Codex `tui_down_after_active`

For the repeated intentional-interruption cases, the maintained matrix SHALL document a concrete two-prompt operator plan covering:

- first prompt submission,
- first intentional interrupt while active,
- second prompt submission after interruption,
- second intentional interrupt while active, and
- final intentional close.

#### Scenario: Maintainer consults the maintained first-wave matrix
- **WHEN** a maintainer prepares to capture or replace one first-wave real fixture
- **THEN** the repo documents a concrete prompt or operator-action plan for that case
- **AND THEN** the documented case matrix makes the targeted transition family explicit before capture begins
- **AND THEN** repeated intentional-interruption cases include a concrete two-prompt, two-interrupt, and close plan rather than a single generic interrupt note

### Requirement: Ground-truth labeling SHALL be direct-snapshot, span-based, and field-complete
Ground-truth labeling for real shared-tracker fixtures SHALL be authored from direct inspection of `recording/pane_snapshots.ndjson`, supported by runtime observations when diagnostics posture matters.

Labels SHALL be span-based over sample ids or sample ranges and SHALL fully specify:

- `diagnostics_availability`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`

#### Scenario: Maintainer labels one real capture from pane snapshots
- **WHEN** a maintainer authors labels for one temporary real capture
- **THEN** the labels are derived from direct snapshot inspection rather than from reducer output
- **AND THEN** the labels cover the full tracked field set for the full sample stream

### Requirement: Promotion of a real fixture SHALL require validated replay evidence and post-labeling MP4 review
The repository SHALL require a documented promotion gate before a temporary real capture becomes a canonical committed fixture.

At minimum, promotion SHALL require:

- zero replay mismatches,
- complete label coverage,
- a generated Markdown summary report, and
- a generated `review.mp4` rendered after recording and state labeling are complete.

#### Scenario: Promotion gate requires validation and video review
- **WHEN** a maintainer prepares to promote one temporary real capture into the committed fixture corpus
- **THEN** the authoring run already has zero-mismatch replay output plus a summary report and labeled review video
- **AND THEN** the fixture is not treated as canonical until those promotion checks have passed

### Requirement: Repeated intentional-interruption fixtures SHALL distinguish both interrupted turns and the final close posture
When maintainers author a repeated intentional-interruption fixture, the labels SHALL distinguish each interrupted turn cycle and the final close posture as separate public-state spans rather than collapsing the whole interaction into one generic interrupted block.

At minimum, the labeled lifecycle SHALL make it possible to distinguish:

- first active turn,
- first interrupted-ready span,
- second active turn,
- second interrupted-ready span, and
- post-close diagnostics-loss posture.

#### Scenario: Maintainer labels a repeated intentional-interruption fixture
- **WHEN** a maintainer authors labels for a repeated intentional-interruption capture
- **THEN** the labels distinguish both interrupted turn cycles and the final close posture as separate spans
- **AND THEN** the labeled spans are sufficient to judge whether the second prompt reset interruption state before the second interrupt occurred

### Requirement: Maintainers SHALL author complex success-interrupt-success fixtures with explicit settle and draft holds
The repository SHALL maintain one complex real-fixture authoring recipe for Claude and one parallel recipe for Codex that captures the lifecycle:

- short prompt submission followed by settled success,
- long prompt with a ready-draft hold before submit,
- first active turn with an active-draft hold while the tool is still running,
- first intentional interrupt followed by an interrupted-ready hold,
- another long prompt with another ready-draft hold before submit,
- second active turn with another active-draft hold,
- second intentional interrupt followed by another interrupted-ready hold, and
- final short prompt submission followed by settled success.

The maintained authoring guidance SHALL specify hold durations long enough for the configured capture cadence and sweep cadence to sample each ready-draft, active-draft, interrupted-ready, and settled-success span reliably.
The maintained authoring guidance SHALL also specify how maintainers keep the visible prompt region on screen during active-draft sampling so the prompt anchor and overlapping draft remain observable in pane snapshots.

#### Scenario: Maintainer follows the complex authoring recipe
- **WHEN** a maintainer captures or replaces one complex success-interrupt-success fixture
- **THEN** the repo documents a concrete operator plan covering both success turns, both interrupted turns, and the intermediate draft holds
- **AND THEN** the documented hold durations make each target span observable to the maintained validation workflow
- **AND THEN** the documented capture plan keeps the prompt region visible during active-draft holds

### Requirement: Complex success-interrupt-success labels SHALL distinguish draft overlap and last-turn reset spans
When maintainers author the complex success-interrupt-success fixtures, the labels SHALL distinguish the public-state spans needed to judge overlapping draft input and stale terminal-result reset.

At minimum, the labeled lifecycle SHALL make it possible to distinguish:

- first settled-success span,
- first ready-draft span with `last_turn.result=none`,
- first active-draft span with `surface.editing_input=yes`,
- first interrupted-ready span,
- second ready-draft span with `last_turn.result=none`,
- second active-draft span with `surface.editing_input=yes`,
- second interrupted-ready span, and
- final settled-success span.

#### Scenario: Maintainer labels the complex fixture from pane snapshots
- **WHEN** a maintainer authors labels for one complex success-interrupt-success capture
- **THEN** the labels distinguish both ready-draft and active-draft spans in addition to both interrupted-ready spans
- **AND THEN** the labeled spans are sufficient to judge whether stale terminal results were cleared before each newer turn

