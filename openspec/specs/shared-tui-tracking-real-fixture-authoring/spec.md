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

