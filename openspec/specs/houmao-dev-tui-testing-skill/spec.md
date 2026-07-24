# houmao-dev-tui-testing-skill Specification

## Purpose
TBD - created by archiving change add-houmao-dev-behavior-testing. Update Purpose after archive.
## Requirements
### Requirement: TUI qualification uses an explicit skill identity
The repository SHALL provide the existing TUI tracking qualification workflow at `skillset/dev/houmao-dev-tui-testing` with frontmatter name `houmao-dev-tui-testing` and matching `agents/openai.yaml` metadata.

The old `skillset/dev/houmao-dev-testing` root and `houmao-dev-testing` invocation SHALL be removed without a compatibility wrapper.

#### Scenario: Maintainer discovers development testing skills
- **WHEN** a maintainer inspects `skillset/dev`
- **THEN** behavior qualification is named `houmao-dev-behavior-testing`
- **AND THEN** TUI tracker qualification is named `houmao-dev-tui-testing`
- **AND THEN** no ambiguous `houmao-dev-testing` skill remains

### Requirement: The rename preserves TUI qualification meaning
The renamed skill SHALL retain the `record`, `label`, `replay`, `compare`, `render-video`, `run-all`, and `help` subcommands and their predecessor-artifact order.

It SHALL continue to freeze high-rate raw terminal evidence before labeling or replay, keep independent manual labels separate from tracker output, replay canonical and varied-cadence streams, compare exact and semantic results, render review evidence, and delegate provider launch to `houmao-dev-launch-agents`.

No command page, evidence gate, public tracked-state vocabulary, comparison rule, video contract, or supported provider SHALL change meaning merely because of the rename.

#### Scenario: Maintainer runs the renamed full workflow
- **WHEN** a maintainer invokes `houmao-dev-tui-testing` with `run-all`
- **THEN** the workflow runs record, blind label, replay, compare, and render stages in the existing order
- **AND THEN** tracker-generated evidence remains unavailable to the label stage

#### Scenario: Maintainer asks for TUI qualification help
- **WHEN** a maintainer invokes `houmao-dev-tui-testing help`
- **THEN** the response identifies TUI state tracking and replay as the skill's purpose
- **AND THEN** it does not claim ownership of live system-skill activation adjudication

### Requirement: TUI artifacts use an unambiguous development root
The renamed skill and tracked TUI qualification documentation SHALL use `tmp/houmao-dev-tui-testing/<run-id>/` for new default run roots and examples.

Tracked invocations, metadata, and development documentation SHALL use `houmao-dev-tui-testing`. Historical Git content and unrelated runtime identifiers SHALL not require rewriting.

#### Scenario: Maintainer creates a new TUI evidence run
- **WHEN** no more specific temporary output path is provided
- **THEN** the skill selects a fresh root below `tmp/houmao-dev-tui-testing/`

#### Scenario: Repository scan checks stale skill identity
- **WHEN** current development skill and qualification files are scanned
- **THEN** they contain no active `houmao-dev-testing` invocation or default root

### Requirement: Development testing skills remain outside runtime packs
Neither `houmao-dev-tui-testing` nor `houmao-dev-behavior-testing` SHALL be declared in the public system-skill manifest, a runtime actor pack, or managed auto-skill projection.

#### Scenario: Runtime catalog is inspected after the rename
- **WHEN** the packaged system-skill manifest is loaded
- **THEN** it contains the same six standalone public roots as before this change
- **AND THEN** it contains neither development testing skill

