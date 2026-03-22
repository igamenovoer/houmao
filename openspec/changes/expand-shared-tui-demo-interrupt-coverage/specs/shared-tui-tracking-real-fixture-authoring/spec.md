## ADDED Requirements

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

## MODIFIED Requirements

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
