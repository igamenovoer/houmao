## ADDED Requirements

### Requirement: Maintainers SHALL author real shared-tracker fixtures from temporary tmux capture runs before promotion
The repository SHALL define a maintainer workflow for real shared tracked-TUI fixtures that uses the existing demo pack to scout live surfaces, capture recorder-backed runs into a temporary authoring subtree under `tmp/`, label ground truth, validate replay, and only then promote selected artifacts into the committed fixture corpus.

The workflow SHALL NOT treat `tests/fixtures/shared_tui_tracking/recorded/` as the first destination for exploratory or partially labeled runs.

#### Scenario: Maintainer authors a real fixture without polluting the committed corpus
- **WHEN** a maintainer begins work on a new Claude or Codex real fixture
- **THEN** the maintainer scouts surfaces with live watch when needed and captures the real session into a temporary authoring run under `tmp/`
- **AND THEN** the maintainer labels and validates that temporary run before any artifact is copied into `tests/fixtures/shared_tui_tracking/recorded/`

### Requirement: The repository SHALL maintain a first-wave real capture matrix with concrete prompts and target transitions
The real-fixture authoring workflow SHALL maintain an explicit first-wave capture matrix that covers both Claude and Codex and names the canonical case ids, prompt shapes, and target transition families to be collected first.

At minimum, that first-wave matrix SHALL include:

- Claude `explicit_success`
- Claude `interrupted_after_active`
- Claude `slash_menu_recovery`
- Claude `tui_down_after_active`
- Codex `explicit_success`
- Codex `interrupted_after_active`
- Codex `tui_down_after_active`

The plan SHALL include concrete operator prompts or actions for each case rather than relying on vague task descriptions.

#### Scenario: Maintainer chooses the next capture from the canonical first wave
- **WHEN** a maintainer prepares to collect real shared-tracker fixtures
- **THEN** the repository provides an explicit first-wave matrix covering both tools and the targeted transition families
- **AND THEN** the maintainer can execute one named case without inventing the prompt and expected transition sequence ad hoc

### Requirement: Ground-truth labeling SHALL be direct-snapshot, span-based, and field-complete
Real-fixture ground truth SHALL be authored from direct inspection of `recording/pane_snapshots.ndjson` and the paired runtime observations for that same capture.

Labels SHALL cover stable spans by `sample_id` and optional `sample_end_id`, and the resulting expectation set SHALL fully specify:

- `diagnostics_availability`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`

Ground truth SHALL NOT be inferred from the standalone reducer output and SHALL NOT omit tracked fields on the assumption that defaults will be filled in later.

#### Scenario: Maintainer labels a real capture from pane snapshots rather than reducer output
- **WHEN** a maintainer classifies one real recorder-backed run
- **THEN** the maintainer reads the pane snapshot sequence directly and uses runtime observations only as supporting diagnostics evidence
- **AND THEN** the saved labels cover the full tracked field set over stable sample spans

### Requirement: Promotion of a real fixture SHALL require validated replay evidence and post-labeling MP4 review
Before a real authoring run is promoted into the canonical committed fixture corpus, the run SHALL satisfy all of the following:

- replay comparison mismatch count is zero,
- label coverage is complete,
- a Markdown summary report has been generated for the authoring run, and
- a `review.mp4` visualization has been generated from the exact labeled pane snapshots for human inspection.

Promotion SHALL copy only the canonical replay artifacts needed by the committed corpus, while temporary authoring reports, issue docs, staged frames, and review videos MAY remain in `tmp/`.

#### Scenario: Maintainer promotes a real fixture into the committed corpus
- **WHEN** a maintainer decides that one temporary authoring run is ready to become canonical
- **THEN** that authoring run has already passed replay validation with zero mismatches
- **AND THEN** after recording and state labeling are complete, the workflow has generated both a summary report and `review.mp4` for the authoring run
- **AND THEN** only the canonical fixture artifacts are promoted into `tests/fixtures/shared_tui_tracking/recorded/`
