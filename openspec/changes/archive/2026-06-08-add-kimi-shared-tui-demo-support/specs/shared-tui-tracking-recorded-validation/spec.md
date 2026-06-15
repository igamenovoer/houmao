## ADDED Requirements

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
