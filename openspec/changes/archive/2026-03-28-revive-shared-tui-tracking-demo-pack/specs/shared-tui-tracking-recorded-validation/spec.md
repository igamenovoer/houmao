## ADDED Requirements

### Requirement: Recorded capture SHALL drive demo-local tool sessions through scenario-owned actions

The restored shared TUI tracking demo pack SHALL provide a recorded-capture workflow under `scripts/demo/shared-tui-tracking-demo-pack/` that launches one real Claude or Codex tmux session from the restored demo-local launch assets, records the pane evidence, and drives the live tool through scenario-owned actions.

The scenario workflow SHALL continue to support actions such as ready waits, active waits, explicit text submission, interrupt, close, and deliberate TUI loss actions.

#### Scenario: One scenario capture builds from demo-local launch assets
- **WHEN** a maintainer runs `recorded-capture` for one restored scenario
- **THEN** the workflow builds a fresh runtime home from a generated run-local agent-definition tree derived from the demo-local launch assets
- **AND THEN** it records pane evidence and runtime observations for that run
- **AND THEN** it drives the live tool through the scenario-owned action sequence

### Requirement: Recorded validation SHALL compare replayed public tracked state against ground truth

The restored recorded-validation workflow SHALL compare human-authored ground truth against the tracker’s public tracked state rather than against raw pane text or internal detector intermediates.

The strict comparison target SHALL remain the public tracked-state fields used by downstream dashboards and reports:

- `diagnostics_availability`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`

The harness SHALL expand `labels.json` into a complete per-sample public-state timeline and SHALL compare replay output against that public-state timeline sample by sample.

#### Scenario: Strict replay validation judges public tracked state per sample
- **WHEN** a maintainer runs `recorded-validate` on one restored fixture root
- **THEN** the workflow expands ground truth from `labels.json` into a complete per-sample public-state timeline
- **AND THEN** it replays the recorded evidence into the shared tracker and compares the replayed public state against ground truth sample by sample

### Requirement: Recorded sweeps SHALL evaluate coarse transition contracts separately from strict ground truth

The restored recorded-sweep workflow SHALL continue to evaluate sweep variants against coarse transition contracts rather than against exact sample-aligned ground-truth timelines.

The sweep contract SHALL support:

- required labels,
- ordered required sequences,
- required or forbidden terminal results, and
- bounded first-occurrence drift relative to the baseline variant.

#### Scenario: Sweep validates repeated interruption and terminal outcome coarsely
- **WHEN** a maintainer runs `recorded-sweep` for one restored fixture and one named sweep
- **THEN** the workflow evaluates all configured variants against the fixture’s transition contract
- **AND THEN** the sweep result can distinguish ordered repeated transitions such as repeated active and interrupted phases without requiring exact sample alignment

### Requirement: Recorded-corpus commands SHALL fail clearly when the committed fixture root is missing

The restored recorded-validation workflow MAY support a configured committed fixture corpus under the configured `fixtures_root`.

When a corpus-oriented command is invoked and that configured fixture root is absent or empty, the command SHALL fail during preflight with a clear error that identifies the missing or empty path instead of assuming a present historical corpus.

#### Scenario: Missing committed corpus fails before replay begins
- **WHEN** a maintainer runs a corpus-oriented restored recorded-validation command
- **AND WHEN** the configured committed fixture root is absent or contains no fixture directories
- **THEN** the command fails before replay begins
- **AND THEN** the error identifies the configured fixture root that is missing or empty
