# shared-tui-tracking-recorded-validation Specification

## Purpose
Define the restored shared TUI tracking recorded-capture, replay-validation, and sweep workflows around public tracked-state comparison.
## Requirements
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

### Requirement: Recorded-corpus commands SHALL preflight missing committed fixture roots clearly

The restored recorded-validation workflow SHALL preflight a configured committed fixture corpus under the configured `fixtures_root` when a corpus-oriented command uses that corpus.

When a corpus-oriented command is invoked and that configured fixture root is absent or empty, the command SHALL fail during preflight with a clear error that identifies the missing or empty path instead of assuming a present historical corpus.

#### Scenario: Missing committed corpus fails before replay begins
- **WHEN** a maintainer runs a corpus-oriented restored recorded-validation command
- **AND WHEN** the configured committed fixture root is absent or contains no fixture directories
- **THEN** the command fails before replay begins
- **AND THEN** the error identifies the configured fixture root that is missing or empty

### Requirement: Recorded validation SHALL support Kimi high-rate and low-rate labeled timelines
Recorded validation SHALL support Kimi fixture or run roots that contain a high-rate snapshot stream, a derived low-rate stream, and labels that apply to one or both streams.

The validation harness SHALL be able to run the same Kimi scenario against both sampling cadences and report whether tracker behavior remains correct when fewer frames are available.

#### Scenario: Kimi recorded validation runs both cadences
- **WHEN** a Kimi recorded-validation fixture contains both 10 fps and derived 2 fps streams
- **THEN** the validation command replays the high-rate stream and compares it with labels
- **AND THEN** it replays the low-rate stream and compares it with labels

#### Scenario: Low-rate validation exposes cadence-sensitive bugs
- **WHEN** the Kimi tracker only works at high sample frequency
- **THEN** the low-rate validation result reports the failed field and sample range
- **AND THEN** the failure is visible before the Kimi tracker is treated as maintained

### Requirement: Kimi recorded validation SHALL use manual labels as the oracle
For Kimi recorded validation, human-authored labels SHALL define the expected public tracked-state timeline.

The validation harness SHALL NOT use raw text snippets, detector notes, or exact matched fragments as the primary correctness oracle.

The validation harness SHALL distinguish development-set runs from held-out test-set runs. Held-out test-set validation SHALL be run after detector implementation and SHALL be reported separately from development-set validation.

#### Scenario: Kimi validation ignores detector-internal notes as pass criteria
- **WHEN** a Kimi detector emits diagnostic notes during replay
- **THEN** validation may include those notes in debug output
- **AND THEN** pass or fail status is determined by labeled parser and public tracked-state expectations

#### Scenario: Held-out Kimi test set is reported separately
- **WHEN** Kimi recorded validation runs for the maintained Kimi profile
- **THEN** the validation report separates development-set results from held-out test-set results
- **AND THEN** the held-out test-set result is visible as an acceptance gate for maintained tracking behavior

### Requirement: Recorded capture SHALL drive Kimi Code through scenario-owned actions
The restored shared TUI tracking demo pack SHALL provide recorded-capture support for Kimi scenarios.

Kimi recorded capture SHALL launch one real Kimi Code tmux session from the demo-local Kimi launch assets, record pane evidence and runtime observations, and drive Kimi through scenario-owned actions.

Kimi scenario control SHALL support ready waits, active waits, text submission, Escape interruption, deliberate process loss, and pattern waits using the same scenario DSL used by other supported tools.

#### Scenario: Kimi recorded capture builds from demo-local launch assets
- **WHEN** a maintainer runs `recorded-capture` for one Kimi scenario
- **THEN** the workflow builds a fresh Kimi runtime home from the generated run-local agent-definition tree
- **AND THEN** it records Kimi pane evidence and runtime observations for that run
- **AND THEN** it drives Kimi through the scenario-owned action sequence

#### Scenario: Kimi interruption uses Escape
- **WHEN** a Kimi recorded-capture scenario executes the `interrupt_turn` action
- **THEN** the workflow sends Escape to the Kimi pane
- **AND THEN** it does not use double Ctrl+C as the primary Kimi interruption path

### Requirement: Kimi first-wave scenarios SHALL cover critical state-tracking surfaces
The restored demo pack SHALL include first-wave Kimi scenarios for manual state-tracking inspection.

At minimum, the Kimi scenario set SHALL cover:

- explicit success from a ready prompt,
- interruption after an active turn,
- approval prompt and rejection,
- footer `thinking` metadata while ready, and
- diagnostics loss after the Kimi TUI process exits or is killed.

#### Scenario: Kimi explicit success scenario is available
- **WHEN** a maintainer lists the shared TUI tracking demo scenarios
- **THEN** a Kimi explicit-success scenario is available for recorded capture
- **AND THEN** it drives Kimi from ready to active to settled ready/success posture

#### Scenario: Kimi approval rejection scenario is available
- **WHEN** a maintainer lists the shared TUI tracking demo scenarios
- **THEN** a Kimi approval-rejection scenario is available for recorded capture
- **AND THEN** it exposes an approval-blocked Kimi surface before the scenario rejects the approval

#### Scenario: Kimi footer-thinking scenario is available
- **WHEN** a maintainer lists the shared TUI tracking demo scenarios
- **THEN** a Kimi footer-thinking-ready scenario is available for recorded capture
- **AND THEN** it leaves a ready prompt visible with footer thinking metadata for inspection

### Requirement: Recorded validation SHALL accept Kimi fixtures and explicit Kimi tool selection
The restored recorded-validation workflow SHALL accept `tool = kimi` from a fixture manifest or from explicit `recorded-validate --tool kimi` selection.

Kimi recorded validation SHALL replay Kimi pane observations through the shared tracker registry and compare the replayed public tracked state against `labels.json` using the same public-state fields as other supported tools.

The workflow SHALL preserve observed Kimi version metadata when fixture manifests or CLI arguments provide it, so profile selection can resolve the maintained `kimi_code` versioned detector.

#### Scenario: Kimi fixture manifest drives replay tool selection
- **WHEN** a fixture root contains `fixture_manifest.json` with `tool` set to `kimi`
- **THEN** `recorded-validate` replays the fixture as a Kimi fixture
- **AND THEN** tracker profile selection resolves through the shared Kimi app id mapping

#### Scenario: Explicit Kimi tool selection works without a manifest
- **WHEN** a maintainer runs `recorded-validate --tool kimi` for a fixture root without `fixture_manifest.json`
- **THEN** the workflow replays the fixture as a Kimi fixture
- **AND THEN** it compares Kimi replay output against the provided labels

### Requirement: Recorded sweeps and corpus inference SHALL understand Kimi fixture paths
The recorded-sweep and corpus-validation workflows SHALL understand Kimi fixture roots and path conventions.

When no fixture manifest is present and the workflow needs to infer a tool from a path, a path component named `kimi` SHALL resolve the tool as Kimi.

Kimi sweep contracts SHALL support the same required-label, required-sequence, terminal-result, forbidden-result, and first-occurrence drift fields as other supported tools.

#### Scenario: Sweep infers Kimi from fixture path
- **WHEN** a maintainer runs `recorded-sweep` against a fixture path containing a `kimi` path component and no fixture manifest
- **THEN** the workflow infers the fixture tool as Kimi
- **AND THEN** it evaluates the selected sweep using Kimi replay state

#### Scenario: Kimi corpus root validates future Kimi fixtures
- **WHEN** a committed fixture corpus later contains Kimi fixture manifests
- **THEN** `recorded-validate-corpus` includes those Kimi fixtures in corpus validation
- **AND THEN** each Kimi fixture is replayed through the shared Kimi tracker profile family

