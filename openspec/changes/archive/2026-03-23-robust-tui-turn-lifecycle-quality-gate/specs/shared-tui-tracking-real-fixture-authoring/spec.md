## ADDED Requirements

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
